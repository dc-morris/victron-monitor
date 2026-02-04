import os
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

VRM_API_BASE = "https://vrmapi.victronenergy.com/v2"


class VRMClient:
    def __init__(self):
        self.token = os.getenv("VRM_TOKEN")
        self.installation_id = os.getenv("VRM_INSTALLATION_ID")

        if not self.token:
            raise ValueError("VRM_TOKEN environment variable is required")
        if not self.installation_id:
            raise ValueError("VRM_INSTALLATION_ID environment variable is required")

        self.headers = {
            "X-Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

    async def get_installation_stats(self) -> Optional[dict]:
        """Get current system stats from VRM."""
        url = f"{VRM_API_BASE}/installations/{self.installation_id}/system-overview"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch VRM stats: {e}")
                return None

    async def get_diagnostic_data(self) -> Optional[dict]:
        """Get diagnostic data with all available attributes."""
        url = f"{VRM_API_BASE}/installations/{self.installation_id}/diagnostics"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch VRM diagnostics: {e}")
                return None

    async def get_widgets(self) -> Optional[dict]:
        """Get widget data for the installation."""
        url = f"{VRM_API_BASE}/installations/{self.installation_id}/widgets/summary"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch VRM widgets: {e}")
                return None

    def parse_diagnostic_data(self, data: dict) -> dict:
        """Parse diagnostic data into a structured format."""
        parsed = {
            "battery_soc": None,
            "battery_voltage": None,
            "battery_current": None,
            "battery_power": None,
            "battery_temperature": None,
            "solar_power": None,
            "solar_voltage": None,
            "solar_current": None,
            "solar_yield_today": None,
            "consumption_power": None,
            "temperature": None,
            "humidity": None,
            "battery_state": None,
        }

        if not data or "records" not in data:
            return parsed

        # VRM diagnostic codes mapping (based on actual GlobalLink 520 data)
        code_mapping = {
            # Battery/System
            "bv": "battery_voltage",        # System voltage
            "bc": "battery_current",        # Battery current
            "bp": "battery_power",          # Battery power
            "SOC": "battery_soc",           # State of charge (if BMV present)
            "bst": "battery_state",         # Battery state (charging/idle/discharging)
            # Solar Charger
            "PVP": "solar_power",           # PV power
            "ScV": "solar_voltage",         # Solar charger voltage
            "ScI": "solar_current",         # Solar charger current
            "ScW": "solar_power",           # Battery watts from solar (alt)
            "YT": "solar_yield_today",      # Yield today
            # Temperature sensor
            "tsT": "temperature",           # Temperature
            "tsH": "humidity",              # Humidity
            # Load
            "SLI": "consumption_power",     # Load current (will need conversion)
        }

        # Records is a list of items
        for item in data.get("records", []):
            code = item.get("code")
            if code in code_mapping:
                try:
                    raw = item.get("rawValue")
                    if raw is not None:
                        if code == "bst":
                            # Battery state is a string
                            parsed[code_mapping[code]] = str(raw)
                        else:
                            parsed[code_mapping[code]] = float(raw)
                except (ValueError, TypeError):
                    pass

        return parsed
