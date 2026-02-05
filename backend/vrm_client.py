import logging
import os
from typing import Optional

import httpx

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
        # Reuse a single HTTP client to prevent memory leaks from repeated SSL context creation
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_installation_stats(self) -> Optional[dict]:
        """Get current system stats from VRM."""
        url = f"{VRM_API_BASE}/installations/{self.installation_id}/system-overview"

        try:
            client = await self._get_client()
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch VRM stats: {e}")
            return None

    async def get_diagnostic_data(self) -> Optional[dict]:
        """Get diagnostic data with all available attributes."""
        url = f"{VRM_API_BASE}/installations/{self.installation_id}/diagnostics"

        try:
            client = await self._get_client()
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch VRM diagnostics: {e}")
            return None

    async def get_widgets(self) -> Optional[dict]:
        """Get widget data for the installation."""
        url = f"{VRM_API_BASE}/installations/{self.installation_id}/widgets/summary"

        try:
            client = await self._get_client()
            response = await client.get(url, headers=self.headers)
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

        # If no SOC from battery monitor, estimate from voltage (12V lead-acid)
        if parsed["battery_soc"] is None and parsed["battery_voltage"] is not None:
            parsed["battery_soc"] = self._estimate_soc_from_voltage(parsed["battery_voltage"])

        return parsed

    def _estimate_soc_from_voltage(self, voltage: float) -> float:
        """
        Estimate SOC from voltage for 12V lead-acid battery.
        This is approximate and works best for resting batteries (no load/charge).

        Voltage table (resting, 25°C):
        12.70V+ = 100%
        12.50V  = 75%
        12.30V  = 50%
        12.10V  = 25%
        11.90V  = 0%
        """
        if voltage >= 12.70:
            return 100.0
        elif voltage <= 11.90:
            return 0.0
        else:
            # Linear interpolation between 11.9V (0%) and 12.7V (100%)
            soc = (voltage - 11.90) / (12.70 - 11.90) * 100.0
            return round(soc, 1)
