import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

# Set up test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_victron.db"
os.environ["BATTERY_CAPACITY_AH"] = "150"
os.environ["BATTERY_VOLTAGE_NOMINAL"] = "12"
os.environ["BATTERY_MIN_SOC"] = "50"

from database import SessionLocal, engine
from main import app, calculate_time_remaining, cleanup_old_readings
from models import Base, EnergyReading
from vrm_client import VRMClient


@pytest.fixture(autouse=True)
def setup_database():
    """Create test database tables before each test, clean up after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "vrm_connected" in data


class TestCurrentEndpoint:
    def test_current_no_data(self):
        response = client.get("/api/current")
        assert response.status_code == 200
        # Either returns data or error message


class TestHistoryEndpoint:
    def test_history_default(self):
        response = client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "readings" in data
        assert isinstance(data["readings"], list)

    def test_history_custom_hours(self):
        response = client.get("/api/history?hours=12")
        assert response.status_code == 200
        data = response.json()
        assert "readings" in data


class TestStatsEndpoint:
    def test_stats(self):
        response = client.get("/api/stats")
        assert response.status_code == 200


class TestVRMClientParsing:
    def test_parse_empty_data(self):
        vrm = VRMClient.__new__(VRMClient)
        result = vrm.parse_diagnostic_data({})
        assert result["battery_voltage"] is None
        assert result["solar_power"] is None
        assert result["temperature"] is None

    def test_parse_no_records(self):
        vrm = VRMClient.__new__(VRMClient)
        result = vrm.parse_diagnostic_data({"success": True})
        assert result["battery_voltage"] is None

    def test_parse_battery_voltage(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "bv", "rawValue": 12.85}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        assert result["battery_voltage"] == 12.85

    def test_parse_solar_power(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "PVP", "rawValue": 150}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        assert result["solar_power"] == 150.0

    def test_parse_temperature(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "tsT", "rawValue": 22.5}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        assert result["temperature"] == 22.5

    def test_parse_humidity(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "tsH", "rawValue": 65.0}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        assert result["humidity"] == 65.0

    def test_parse_battery_state(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "bst", "rawValue": "idle"}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        assert result["battery_state"] == "idle"

    def test_parse_full_diagnostic(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "bv", "rawValue": 12.95},
                {"code": "bc", "rawValue": 0.5},
                {"code": "bp", "rawValue": 6},
                {"code": "bst", "rawValue": "charging"},
                {"code": "PVP", "rawValue": 120},
                {"code": "ScV", "rawValue": 18.5},
                {"code": "ScI", "rawValue": 6.5},
                {"code": "YT", "rawValue": 0.85},
                {"code": "tsT", "rawValue": 21.3},
                {"code": "tsH", "rawValue": 58.0},
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        assert result["battery_voltage"] == 12.95
        assert result["battery_current"] == 0.5
        assert result["battery_power"] == 6.0
        assert result["battery_state"] == "charging"
        assert result["solar_power"] == 120.0
        assert result["solar_voltage"] == 18.5
        assert result["solar_current"] == 6.5
        assert result["solar_yield_today"] == 0.85
        assert result["temperature"] == 21.3
        assert result["humidity"] == 58.0

    def test_parse_invalid_value(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "success": True,
            "records": [
                {"code": "bv", "rawValue": "invalid"}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        # Should not crash, just leave as None
        assert result["battery_voltage"] is None


class TestSOCEstimation:
    def test_soc_full_battery(self):
        vrm = VRMClient.__new__(VRMClient)
        assert vrm._estimate_soc_from_voltage(12.70) == 100.0
        assert vrm._estimate_soc_from_voltage(12.85) == 100.0
        assert vrm._estimate_soc_from_voltage(13.0) == 100.0

    def test_soc_empty_battery(self):
        vrm = VRMClient.__new__(VRMClient)
        assert vrm._estimate_soc_from_voltage(11.90) == 0.0
        assert vrm._estimate_soc_from_voltage(11.50) == 0.0

    def test_soc_mid_range(self):
        vrm = VRMClient.__new__(VRMClient)
        # 12.30V should be ~50%
        soc = vrm._estimate_soc_from_voltage(12.30)
        assert 49 <= soc <= 51

        # 12.50V should be ~75%
        soc = vrm._estimate_soc_from_voltage(12.50)
        assert 74 <= soc <= 76

    def test_soc_applied_when_no_monitor(self):
        vrm = VRMClient.__new__(VRMClient)
        data = {
            "records": [
                {"code": "bv", "rawValue": 12.50}
            ]
        }
        result = vrm.parse_diagnostic_data(data)
        # Should have estimated SOC since no BMV data
        assert result["battery_soc"] is not None
        assert 74 <= result["battery_soc"] <= 76


class TestTimeRemaining:
    def test_discharging(self):
        # 150Ah * 12V = 1800Wh capacity
        # At 50% SOC = 900Wh remaining
        # At 100W net consumption = 9 hours to empty
        result = calculate_time_remaining(
            soc=50.0,
            consumption_power=100.0,
            solar_power=0.0
        )
        assert result["is_discharging"] is True
        assert result["is_charging"] is False
        assert result["net_power"] == 100.0
        assert result["hours_to_empty"] == 9.0
        # To 50% from 50% = 0 hours
        assert result["hours_to_min"] == 0

    def test_discharging_with_partial_solar(self):
        # 100W consumption - 60W solar = 40W net
        # At 75% SOC = 1350Wh, at 40W = 33.75 hours
        result = calculate_time_remaining(
            soc=75.0,
            consumption_power=100.0,
            solar_power=60.0
        )
        assert result["is_discharging"] is True
        assert result["net_power"] == 40.0
        assert result["hours_to_empty"] == 33.8  # rounded

    def test_charging(self):
        # 50W consumption - 150W solar = -100W (charging)
        # At 50% SOC, need 900Wh to full
        # At 100W charge = 9 hours to full
        result = calculate_time_remaining(
            soc=50.0,
            consumption_power=50.0,
            solar_power=150.0
        )
        assert result["is_charging"] is True
        assert result["is_discharging"] is False
        assert result["net_power"] == -100.0
        assert result["hours_to_full"] == 9.0

    def test_idle_at_full(self):
        # At 100% SOC with no net power
        result = calculate_time_remaining(
            soc=100.0,
            consumption_power=50.0,
            solar_power=50.0
        )
        assert result["is_charging"] is False
        assert result["is_discharging"] is False
        assert result["net_power"] == 0.0

    def test_no_soc(self):
        result = calculate_time_remaining(
            soc=None,
            consumption_power=100.0,
            solar_power=0.0
        )
        assert result["is_discharging"] is False
        assert result["is_charging"] is False
        assert result["hours_to_empty"] is None

    def test_hours_to_min_soc(self):
        # At 80% SOC, 50W net consumption
        # 1800Wh * 0.80 = 1440Wh to empty
        # 1800Wh * (0.80 - 0.50) = 540Wh to 50%
        # 540Wh / 50W = 10.8 hours to min
        result = calculate_time_remaining(
            soc=80.0,
            consumption_power=50.0,
            solar_power=0.0
        )
        assert result["hours_to_min"] == 10.8


class TestCleanupOldReadings:
    def test_deletes_old_readings(self):
        """Readings older than 7 days should be deleted."""
        db = SessionLocal()
        try:
            old_reading = EnergyReading(
                timestamp=datetime.utcnow() - timedelta(days=8),
                battery_voltage=12.5,
                solar_power=100.0,
            )
            db.add(old_reading)
            db.commit()
            assert db.query(EnergyReading).count() == 1
        finally:
            db.close()

        cleanup_old_readings()

        db = SessionLocal()
        try:
            assert db.query(EnergyReading).count() == 0
        finally:
            db.close()

    def test_keeps_recent_readings(self):
        """Readings within the last 7 days should be kept."""
        db = SessionLocal()
        try:
            recent_reading = EnergyReading(
                timestamp=datetime.utcnow() - timedelta(days=3),
                battery_voltage=12.8,
                solar_power=200.0,
            )
            db.add(recent_reading)
            db.commit()
        finally:
            db.close()

        cleanup_old_readings()

        db = SessionLocal()
        try:
            assert db.query(EnergyReading).count() == 1
        finally:
            db.close()

    def test_mixed_old_and_recent(self):
        """Only old readings should be deleted, recent ones kept."""
        db = SessionLocal()
        try:
            old = EnergyReading(
                timestamp=datetime.utcnow() - timedelta(days=10),
                battery_voltage=12.0,
            )
            recent = EnergyReading(
                timestamp=datetime.utcnow() - timedelta(hours=1),
                battery_voltage=12.9,
            )
            db.add_all([old, recent])
            db.commit()
        finally:
            db.close()

        cleanup_old_readings()

        db = SessionLocal()
        try:
            remaining = db.query(EnergyReading).all()
            assert len(remaining) == 1
            assert remaining[0].battery_voltage == 12.9
        finally:
            db.close()


class TestSunEndpoint:
    def test_sun_returns_data(self):
        response = client.get("/api/sun")
        assert response.status_code == 200
        data = response.json()
        assert "sunrise" in data
        assert "sunset" in data
        assert "daylight_remaining_hours" in data
        assert "is_daylight" in data
        assert "location" in data
