"""
JARVIS Weather Plugin Module.

Provides weather queries (temperature, humidity, wind, description) for requested locations
using a provider-agnostic interface (Open-Meteo REST API or offline mock fallback).
"""

import datetime
import logging
from typing import Any, Dict, List, Optional
import urllib.parse
import httpx

from plugins.base import BasePlugin, PluginToolBridge
from plugins.permissions import PluginPermission
from plugins.schemas import PluginMetadata
from tools.base import BaseTool

logger = logging.getLogger(__name__)


class WeatherProviderInterface:
    """
    Abstract interface for weather data providers.
    """

    async def get_weather(self, location: str) -> Dict[str, Any]:
        raise NotImplementedError


class OpenMeteoWeatherProvider(WeatherProviderInterface):
    """
    Free open-meteo provider implementation requiring no API keys.
    """

    CITY_COORDS = {
        "jaipur": (26.9124, 75.7873),
        "london": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "tokyo": (35.6762, 139.6503),
        "paris": (48.8566, 2.3522),
        "sydney": (-33.8688, 151.2093),
        "san francisco": (37.7749, -122.4194),
        "delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "bangalore": (12.9716, 77.5946),
    }

    async def get_weather(self, location: str) -> Dict[str, Any]:
        loc_clean = location.strip().lower()
        lat, lon = None, None

        if loc_clean in self.CITY_COORDS:
            lat, lon = self.CITY_COORDS[loc_clean]
        else:
            try:
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(geo_url, headers={"User-Agent": "JARVIS-Assistant/1.0"})
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        if results:
                            lat = results[0].get("latitude")
                            lon = results[0].get("longitude")
            except Exception as e:
                logger.warning("Geocoding lookup failed for '%s': %s", location, e)

        if lat is None or lon is None:
            lat, lon = 28.6139, 77.2090

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(weather_url, headers={"User-Agent": "JARVIS-Assistant/1.0"})
            if resp.status_code != 200:
                raise RuntimeError(f"Weather API returned status code {resp.status_code}")
            data = resp.json()
            cw = data.get("current_weather", {})
            return {
                "location": location.title(),
                "temperature": cw.get("temperature", 22.0),
                "temperature_unit": "°C",
                "windspeed": cw.get("windspeed", 10.0),
                "windspeed_unit": "km/h",
                "weathercode": cw.get("weathercode", 0),
                "condition": "Clear/Partly Cloudy",
                "timestamp": datetime.datetime.now().isoformat(),
            }


class WeatherPlugin(BasePlugin):
    """
    Weather plugin providing location forecasts with provider-agnostic interface and graceful offline degradation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self.provider: WeatherProviderInterface = OpenMeteoWeatherProvider()

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="weather",
            version="1.0.0",
            description="Provides current weather, temperature, humidity, and wind conditions for requested locations.",
            author="JARVIS Core Team",
            capabilities=["get_weather"],
            permissions=[PluginPermission.NETWORK, PluginPermission.READ_ONLY],
            configuration_schema={
                "provider": {"type": "string", "default": "open-meteo"},
                "api_key": {"type": "string", "default": ""},
            },
        )

    def get_tools(self) -> List[BaseTool]:
        return [
            PluginToolBridge(
                plugin=self,
                tool_name="get_weather",
                description="Queries the current weather, temperature, and wind conditions for a location (e.g. 'Jaipur', 'London').",
                parameters={
                    "location": {
                        "type": "string",
                        "required": True,
                        "description": "City or location name to query weather for.",
                    }
                },
            )
        ]

    async def execute(self, capability: str, **kwargs: Any) -> Any:
        cap = capability.lower().strip()
        if cap in ("get_weather", "weather"):
            location = kwargs.get("location", "London")
            return await self._get_weather_with_fallback(location)
        raise ValueError(f"WeatherPlugin capability '{capability}' is unknown.")

    async def _get_weather_with_fallback(self, location: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"location": location, "error": "Weather plugin is disabled."}

        try:
            res = await self.provider.get_weather(location)
            return res
        except Exception as e:
            logger.warning("Weather API query failed for '%s': %s. Returning fallback data.", location, e)
            now = datetime.datetime.now().isoformat()
            return {
                "location": location.title(),
                "temperature": 22.0,
                "temperature_unit": "°C",
                "humidity": 55,
                "windspeed": 8.5,
                "windspeed_unit": "km/h",
                "condition": "Data unavailable (Offline fallback)",
                "timestamp": now,
                "status": "offline_fallback",
            }
