import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import os

# Set up test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_victron.db"

from main import app
from database import init_db, engine
from models import Base
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
