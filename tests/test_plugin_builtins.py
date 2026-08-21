"""
Unit and integration tests for Built-in Plugins (System, Weather, WebSearch).

Verifies capability execution, provider abstractions, parameters,
and offline/network failure degradation.
"""

import pytest
from typing import Any, Dict

from plugins.builtins.system import SystemPlugin
from plugins.builtins.weather import WeatherPlugin, OpenMeteoWeatherProvider
from plugins.builtins.web_search import WebSearchPlugin, DuckDuckGoSearchProvider


@pytest.mark.asyncio
async def test_system_plugin_capabilities():
    plugin = SystemPlugin()
    await plugin.initialize()

    # Check metadata
    meta = plugin.metadata
    assert meta.name == "system"
    assert "get_system_status" in meta.capabilities

    # Check bridged tools
    tools = plugin.get_tools()
    assert len(tools) >= 5

    # Execute datetime capability
    dt_res = await plugin.execute("get_current_datetime")
    assert "friendly_text" in dt_res

    # Execute math calculator capability
    calc_res = await plugin.execute("calculator", expression="10 + 20")
    assert calc_res["result"] == 30.0

    # Execute system status capability
    sys_res = await plugin.execute("get_system_status")
    assert "cpu_load_averages" in sys_res


@pytest.mark.asyncio
async def test_weather_plugin_and_fallback():
    plugin = WeatherPlugin()
    await plugin.initialize()

    meta = plugin.metadata
    assert meta.name == "weather"

    # Query weather with provider or graceful offline fallback
    res = await plugin.execute("get_weather", location="Jaipur")
    assert res["location"].lower() == "jaipur"
    assert "temperature" in res

    # Force failure on provider to test offline degradation
    class BrokenWeatherProvider:
        async def get_weather(self, location: str) -> Dict[str, Any]:
            raise ConnectionError("Network unreachable")

    plugin.provider = BrokenWeatherProvider()
    fallback_res = await plugin.execute("get_weather", location="London")
    assert fallback_res["location"] == "London"
    assert fallback_res["temperature"] == 22.0
    assert fallback_res["status"] == "offline_fallback"


@pytest.mark.asyncio
async def test_web_search_plugin_and_fallback():
    plugin = WebSearchPlugin()
    await plugin.initialize()

    meta = plugin.metadata
    assert meta.name == "web_search"

    # Query web search with fallback handling
    res = await plugin.execute("web_search", query="Python asyncio tutorial")
    assert res["query"] == "Python asyncio tutorial"
    assert "results" in res

    # Test empty query handling
    empty_res = await plugin.execute("web_search", query="")
    assert "error" in empty_res

    # Force failure on provider to verify offline fallback response
    class BrokenSearchProvider:
        async def search(self, query: str, num_results: int = 3):
            raise TimeoutError("Search timed out")

    plugin.provider = BrokenSearchProvider()
    fallback_res = await plugin.execute("web_search", query="test query")
    assert fallback_res["query"] == "test query"
    assert fallback_res["status"] == "offline_fallback"
    assert fallback_res["count"] == 0
