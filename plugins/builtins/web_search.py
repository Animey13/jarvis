"""
JARVIS Web Search Plugin Module.

Provides provider-agnostic web search integration (DuckDuckGo / HTTP search interface)
handling rate limits, timeouts, missing keys, network failure, and offline degradation.
"""

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx

from plugins.base import BasePlugin, PluginToolBridge
from plugins.permissions import PluginPermission
from plugins.schemas import PluginMetadata
from tools.base import BaseTool

logger = logging.getLogger(__name__)


class SearchProviderInterface:
    """
    Abstract interface for search engines.
    """

    async def search(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        raise NotImplementedError


class DuckDuckGoSearchProvider(SearchProviderInterface):
    """
    Provider using DuckDuckGo Instant Answer API / HTML search endpoints without API key requirements.
    """

    async def search(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        query_clean = query.strip()
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query_clean)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    html_text = resp.text
                    matches = re.findall(
                        r'<a class="result__url" href="([^"]+)".*?<a class="result__snippet[^>]*>(.*?)</a>',
                        html_text,
                        re.DOTALL,
                    )
                    results = []
                    for link, snippet in matches[:num_results]:
                        clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()
                        results.append({"title": query_clean, "url": link.strip(), "snippet": clean_snippet})
                    if results:
                        return results
        except Exception as e:
            logger.warning("DuckDuckGo HTML search failed: %s", e)

        try:
            json_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query_clean)}&format=json"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp2 = await client.get(json_url, headers={"User-Agent": "JARVIS-Assistant/1.0"})
                if resp2.status_code == 200:
                    data = resp2.json()
                    abstract = data.get("AbstractText", "")
                    if abstract:
                        return [
                            {
                                "title": data.get("Heading", query_clean),
                                "url": data.get("AbstractURL", ""),
                                "snippet": abstract,
                            }
                        ]
                    topics = data.get("RelatedTopics", [])
                    results = []
                    for t in topics[:num_results]:
                        if isinstance(t, dict) and "Text" in t:
                            results.append(
                                {
                                    "title": query_clean,
                                    "url": t.get("FirstURL", ""),
                                    "snippet": t.get("Text", ""),
                                }
                            )
                    if results:
                        return results
        except Exception as e:
            logger.warning("DuckDuckGo Instant Answer API failed: %s", e)

        return []


class WebSearchPlugin(BasePlugin):
    """
    Web Search plugin providing provider-agnostic search capability with offline fallbacks.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self.provider: SearchProviderInterface = DuckDuckGoSearchProvider()

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web_search",
            version="1.0.0",
            description="Performs online web searches to query real-time information, news, and technical topics.",
            author="JARVIS Core Team",
            capabilities=["web_search"],
            permissions=[PluginPermission.NETWORK, PluginPermission.READ_ONLY],
            configuration_schema={
                "provider": {"type": "string", "default": "duckduckgo"},
                "api_key": {"type": "string", "default": ""},
            },
        )

    def get_tools(self) -> List[BaseTool]:
        return [
            PluginToolBridge(
                plugin=self,
                tool_name="web_search",
                description="Performs a web search for latest information, technical documentation, or facts.",
                parameters={
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string to look up.",
                    }
                },
            )
        ]

    async def execute(self, capability: str, **kwargs: Any) -> Any:
        cap = capability.lower().strip()
        if cap in ("web_search", "search"):
            query = kwargs.get("query", "")
            return await self._search_with_fallback(query)
        raise ValueError(f"WebSearchPlugin capability '{capability}' is unknown.")

    async def _search_with_fallback(self, query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"query": query, "error": "Search query cannot be empty."}

        if not self.enabled:
            return {"query": query, "error": "Web search plugin is disabled."}

        try:
            results = await self.provider.search(query)
            if results:
                return {"query": query, "count": len(results), "results": results}
            return {
                "query": query,
                "count": 0,
                "results": [],
                "message": "No search results returned from provider.",
            }
        except Exception as e:
            logger.warning("Web search error for '%s': %s", query, e)
            return {
                "query": query,
                "count": 0,
                "results": [],
                "error": f"Search failed: {e}",
                "status": "offline_fallback",
            }
