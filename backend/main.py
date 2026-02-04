import os
import json
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, get_db
from models import EnergyReading
from vrm_client import VRMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

vrm_client: VRMClient = None
scheduler = AsyncIOScheduler()


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
                raw_data=json.dumps(diagnostics)
            )
            db.add(reading)
            db.commit()
            logger.info(f"Stored reading: SOC={parsed['battery_soc']}%, Solar={parsed['solar_power']}W")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching/storing data: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vrm_client

    # Initialize database
    init_db()

    # Initialize VRM client
    try:
        vrm_client = VRMClient()
        logger.info("VRM client initialized")
    except ValueError as e:
        logger.error(f"VRM client initialization failed: {e}")
        logger.warning("Running without VRM connection - configure VRM_TOKEN and VRM_INSTALLATION_ID")

    # Start scheduler for periodic data fetching
    if vrm_client:
        scheduler.add_job(fetch_and_store_data, 'interval', minutes=1, id='fetch_vrm_data')
        scheduler.start()
        # Fetch initial data
        await fetch_and_store_data()

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="Campervan Monitor", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

    return {
        "timestamp": reading.timestamp.isoformat(),
        "battery": {
            "soc": reading.battery_soc,
            "voltage": reading.battery_voltage,
            "current": reading.battery_current,
            "power": reading.battery_power,
            "state": reading.battery_state,
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
async def get_history(hours: int = 24, db: Session = Depends(get_db)):
    """Get historical readings."""
    since = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(EnergyReading).filter(
        EnergyReading.timestamp >= since
    ).order_by(EnergyReading.timestamp).all()

    return {
        "readings": [
            {
                "timestamp": r.timestamp.isoformat(),
                "battery_voltage": r.battery_voltage,
                "battery_power": r.battery_power,
                "solar_power": r.solar_power,
                "temperature": r.temperature,
            }
            for r in readings
        ]
    }


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get summary statistics for today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    readings = db.query(EnergyReading).filter(
        EnergyReading.timestamp >= today_start
    ).all()

    if not readings:
        return {"error": "No data for today"}

    solar_powers = [r.solar_power for r in readings if r.solar_power is not None]
    consumption_powers = [r.consumption_power for r in readings if r.consumption_power is not None]

    return {
        "today": {
            "solar_peak": max(solar_powers) if solar_powers else None,
            "solar_avg": sum(solar_powers) / len(solar_powers) if solar_powers else None,
            "consumption_avg": sum(consumption_powers) / len(consumption_powers) if consumption_powers else None,
            "readings_count": len(readings),
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
