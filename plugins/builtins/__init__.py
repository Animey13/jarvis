"""
JARVIS Built-in Plugins Package Initialization.
"""

from plugins.builtins.system import SystemPlugin
from plugins.builtins.weather import WeatherPlugin
from plugins.builtins.web_search import WebSearchPlugin

__all__ = ["SystemPlugin", "WeatherPlugin", "WebSearchPlugin"]
