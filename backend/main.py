import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import EnergyReading
from vrm_client import VRMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Battery configuration (configurable via environment variables)
BATTERY_CAPACITY_AH = float(os.getenv("BATTERY_CAPACITY_AH", "100"))
BATTERY_VOLTAGE_NOMINAL = float(os.getenv("BATTERY_VOLTAGE_NOMINAL", "12"))
BATTERY_MIN_SOC = float(os.getenv("BATTERY_MIN_SOC", "50"))  # Don't discharge below this %

# Location for sunrise/sunset (default: London)
LOCATION_LAT = float(os.getenv("LOCATION_LAT", "51.5074"))
LOCATION_LON = float(os.getenv("LOCATION_LON", "-0.1278"))
LOCATION_NAME = os.getenv("LOCATION_NAME", "London")

# Optional weather API
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

vrm_client: VRMClient = None
http_client: httpx.AsyncClient = None
scheduler = AsyncIOScheduler()


def calculate_time_remaining(
    soc: Optional[float],
    consumption_power: Optional[float],
    solar_power: Optional[float],
) -> dict:
    """
    Calculate estimated battery time remaining/to full.

    Returns dict with:
    - hours_to_empty: time until 0% SOC (when discharging)
    - hours_to_min: time until minimum safe SOC (when discharging)
    - hours_to_full: time until 100% SOC (when charging)
    - net_power: net power flow (positive = discharging, negative = charging)
    - is_discharging: True if net consumption > 0
    - is_charging: True if net consumption < 0
    """
    result = {
        "hours_to_empty": None,
        "hours_to_min": None,
        "hours_to_full": None,
        "net_power": None,
        "is_discharging": False,
        "is_charging": False,
    }

    if soc is None:
        return result

    # Calculate net power flow (positive = discharging, negative = charging)
    consumption = consumption_power or 0
    solar = solar_power or 0
    net = consumption - solar

    result["net_power"] = round(net, 1)

    # Battery capacity in Wh
    capacity_wh = BATTERY_CAPACITY_AH * BATTERY_VOLTAGE_NOMINAL

    if net > 0:
        # Discharging
        result["is_discharging"] = True

        # Energy remaining to empty
        energy_to_empty = capacity_wh * (soc / 100)
        result["hours_to_empty"] = round(energy_to_empty / net, 1)

        # Energy remaining to minimum SOC
        if soc > BATTERY_MIN_SOC:
            energy_to_min = capacity_wh * ((soc - BATTERY_MIN_SOC) / 100)
            result["hours_to_min"] = round(energy_to_min / net, 1)
        else:
            result["hours_to_min"] = 0

    elif net < 0 and soc < 100:
        # Charging (net is negative, so use absolute value)
        result["is_charging"] = True
        charge_power = abs(net)

        # Energy needed to reach 100%
        energy_to_full = capacity_wh * ((100 - soc) / 100)
        result["hours_to_full"] = round(energy_to_full / charge_power, 1)

    return result


async def fetch_and_store_data():
    """Fetch data from VRM and store in database."""
    from database import SessionLocal

    try:
        diagnostics = await vrm_client.get_diagnostic_data()
        if not diagnostics:
            logger.warning("No diagnostic data received from VRM")
            return

        parsed = vrm_client.parse_diagnostic_data(diagnostics)

        db = SessionLocal()
        try:
            reading = EnergyReading(
                battery_soc=parsed["battery_soc"],
                battery_voltage=parsed["battery_voltage"],
                battery_current=parsed["battery_current"],
                battery_power=parsed["battery_power"],
                battery_temperature=parsed["battery_temperature"],
                solar_power=parsed["solar_power"],
                solar_voltage=parsed["solar_voltage"],
                solar_current=parsed["solar_current"],
                solar_yield_today=parsed["solar_yield_today"],
                consumption_power=parsed["consumption_power"],
                temperature=parsed["temperature"],
                humidity=parsed["humidity"],
                battery_state=parsed["battery_state"],
            )
            db.add(reading)
            db.commit()
            logger.info(f"Stored reading: SOC={parsed['battery_soc']}%, Solar={parsed['solar_power']}W")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching/storing data: {e}")


def cleanup_old_readings():
    """Delete readings older than 7 days to prevent unbounded database growth."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        deleted = db.query(EnergyReading).filter(
            EnergyReading.timestamp < cutoff
        ).delete()
        db.commit()
        if deleted:
            logger.info(f"Cleaned up {deleted} readings older than 7 days")
    except Exception as e:
        logger.error(f"Error cleaning up old readings: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vrm_client, http_client

    # Initialize database
    init_db()

    # Initialize shared HTTP client
    http_client = httpx.AsyncClient(timeout=10.0)

    # Initialize VRM client
    try:
        vrm_client = VRMClient()
        logger.info("VRM client initialized")
    except ValueError as e:
        logger.error(f"VRM client initialization failed: {e}")
        logger.warning("Running without VRM connection - configure VRM_TOKEN and VRM_INSTALLATION_ID")

    # Start scheduler for periodic data fetching and cleanup
    scheduler.add_job(cleanup_old_readings, 'interval', hours=1, id='cleanup_old_readings')
    if vrm_client:
        scheduler.add_job(fetch_and_store_data, 'interval', minutes=1, id='fetch_vrm_data')
    scheduler.start()
    # Run cleanup on startup
    cleanup_old_readings()
    if vrm_client:
        # Fetch initial data
        await fetch_and_store_data()

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()
    if vrm_client:
        await vrm_client.close()
    if http_client:
        await http_client.aclose()


app = FastAPI(title="Victron Monitor", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://victron-monitor.fly.dev",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/current")
async def get_current_data(db: Session = Depends(get_db)):
    """Get the most recent reading."""
    reading = db.query(EnergyReading).order_by(desc(EnergyReading.timestamp)).first()

    if not reading:
        return {"error": "No data available"}

    time_remaining = calculate_time_remaining(
        reading.battery_soc,
        reading.consumption_power,
        reading.solar_power,
    )

    return {
        "timestamp": reading.timestamp.isoformat(),
        "battery": {
            "soc": reading.battery_soc,
            "voltage": reading.battery_voltage,
            "current": reading.battery_current,
            "power": reading.battery_power,
            "state": reading.battery_state,
            "time_remaining": time_remaining,
            "capacity_ah": BATTERY_CAPACITY_AH,
            "min_soc": BATTERY_MIN_SOC,
        },
        "solar": {
            "power": reading.solar_power,
            "voltage": reading.solar_voltage,
            "current": reading.solar_current,
            "yield_today": reading.solar_yield_today,
        },
        "consumption": {
            "power": reading.consumption_power,
        },
        "environment": {
            "temperature": reading.temperature,
            "humidity": reading.humidity,
        }
    }


@app.get("/api/history")
async def get_history(hours: int = Query(24, ge=1, le=168), db: Session = Depends(get_db)):
    """Get historical readings (max 168 hours / 1 week).

    For ranges over 24 hours, readings are downsampled to keep response
    size bounded (~1440 points max) and reduce memory usage.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(EnergyReading).filter(
        EnergyReading.timestamp >= since
    ).order_by(EnergyReading.timestamp).all()

    # Downsample for large ranges: keep ~1440 points (one per minute for 24h)
    step = max(1, len(readings) // 1440)
    sampled = readings[::step] if step > 1 else readings

    return {
        "readings": [
            {
                "timestamp": r.timestamp.isoformat(),
                "battery_voltage": r.battery_voltage,
                "battery_current": r.battery_current,
                "battery_power": r.battery_power,
                "battery_state": r.battery_state,
                "solar_power": r.solar_power,
                "solar_voltage": r.solar_voltage,
                "solar_current": r.solar_current,
                "solar_yield_today": r.solar_yield_today,
                "temperature": r.temperature,
                "humidity": r.humidity,
            }
            for r in sampled
        ]
    }


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get summary statistics for today using SQL aggregation."""
    from sqlalchemy import func

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Use SQL aggregation instead of loading all records into memory
    stats = db.query(
        func.max(EnergyReading.solar_power).label("solar_peak"),
        func.avg(EnergyReading.solar_power).label("solar_avg"),
        func.avg(EnergyReading.consumption_power).label("consumption_avg"),
        func.count(EnergyReading.id).label("readings_count"),
    ).filter(
        EnergyReading.timestamp >= today_start
    ).first()

    if not stats or stats.readings_count == 0:
        return {"error": "No data for today"}

    return {
        "today": {
            "solar_peak": stats.solar_peak,
            "solar_avg": round(stats.solar_avg, 2) if stats.solar_avg else None,
            "consumption_avg": round(stats.consumption_avg, 2) if stats.consumption_avg else None,
            "readings_count": stats.readings_count,
        }
    }


@app.post("/api/refresh")
async def refresh_data():
    """Manually trigger a data refresh from VRM."""
    if not vrm_client:
        raise HTTPException(status_code=503, detail="VRM client not configured")

    await fetch_and_store_data()
    return {"status": "ok"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "vrm_connected": vrm_client is not None
    }


@app.get("/api/sun")
async def get_sun_info():
    """Get sunrise, sunset, and daylight information."""
    from zoneinfo import ZoneInfo

    from astral import LocationInfo
    from astral.sun import sun

    try:
        location = LocationInfo(
            name=LOCATION_NAME,
            region="",
            timezone="Europe/London",
            latitude=LOCATION_LAT,
            longitude=LOCATION_LON,
        )

        # Get sun times for today
        tz = ZoneInfo("Europe/London")
        now = datetime.now(tz)
        s = sun(location.observer, date=now.date(), tzinfo=tz)

        sunrise = s["sunrise"]
        sunset = s["sunset"]

        # Calculate daylight remaining
        if now < sunrise:
            # Before sunrise
            daylight_remaining = (sunset - sunrise).total_seconds() / 3600
            is_daylight = False
        elif now > sunset:
            # After sunset
            daylight_remaining = 0
            is_daylight = False
        else:
            # During daylight
            daylight_remaining = (sunset - now).total_seconds() / 3600
            is_daylight = True

        result = {
            "sunrise": sunrise.strftime("%H:%M"),
            "sunset": sunset.strftime("%H:%M"),
            "daylight_remaining_hours": round(daylight_remaining, 1),
            "is_daylight": is_daylight,
            "location": LOCATION_NAME,
        }

        # Add weather if API key is configured
        if OPENWEATHER_API_KEY and http_client:
            try:
                resp = await http_client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "lat": LOCATION_LAT,
                        "lon": LOCATION_LON,
                        "appid": OPENWEATHER_API_KEY,
                        "units": "metric",
                    },
                )
                if resp.status_code == 200:
                    weather = resp.json()
                    result["weather"] = {
                        "condition": weather["weather"][0]["main"],
                        "description": weather["weather"][0]["description"],
                        "icon": weather["weather"][0]["icon"],
                        "temp": weather["main"]["temp"],
                        "clouds": weather["clouds"]["all"],
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch weather: {e}")

        return result

    except Exception as e:
        logger.error(f"Failed to calculate sun times: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate sun times") from None
