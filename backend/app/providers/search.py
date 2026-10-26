"""
Web search used to ground the planner in real, current places (search first, then write).

Tavily and Exa both return title + URL + a text snippet per result, which is all the
agents need. Results are cached by the caller, so a destination is searched once a day.
"""

from abc import ABC, abstractmethod

import httpx
from loguru import logger

from app.common.schemas import APIModel

SNIPPET_CHARS = 600


class WebResult(APIModel):
    title: str
    url: str
    snippet: str = ""
    published_date: str | None = None
    image: str | None = None


class WebSearchProvider(ABC):
    name = "base"

    @abstractmethod
    async def search(self, query: str, max_results: int = 8) -> list[WebResult]: ...


class NoWebSearch(WebSearchProvider):
    """Grounding disabled: agents answer from the model's own knowledge."""

    name = "none"

    async def search(self, query: str, max_results: int = 8) -> list[WebResult]:
        return []


class MockWebSearch(WebSearchProvider):
    name = "mock"

    async def search(self, query: str, max_results: int = 8) -> list[WebResult]:
        slug = "-".join(query.lower().split())[:60]
        return [
            WebResult(
                title=f"{query.title()}: guide part {i + 1}",
                url=f"https://example.com/{slug}/{i + 1}",
                snippet=f"Result {i + 1} about {query}. Opening hours, prices and tips from recent visitors.",
            )
            for i in range(min(max_results, 5))
        ]


class TavilySearch(WebSearchProvider):
    name = "tavily"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is required for SEARCH_PROVIDER=tavily")
        self.http, self.key = http, api_key

    async def search(self, query: str, max_results: int = 8) -> list[WebResult]:
        try:
            resp = await self.http.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {self.key}"},
                json={"query": query, "search_depth": "basic", "max_results": max_results, "include_answer": False, "topic": "general"},
                timeout=20,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Tavily search failed for '{query}': {exc}")
            return []
        return [
            WebResult(title=r.get("title") or r["url"], url=r["url"], snippet=(r.get("content") or "")[:SNIPPET_CHARS], published_date=r.get("published_date"))
            for r in resp.json().get("results", [])
            if r.get("url")
        ]


class ExaSearch(WebSearchProvider):
    name = "exa"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        if not api_key:
            raise RuntimeError("EXA_API_KEY is required for SEARCH_PROVIDER=exa")
        self.http, self.key = http, api_key

    async def search(self, query: str, max_results: int = 8) -> list[WebResult]:
        try:
            resp = await self.http.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": self.key},
                json={"query": query, "type": "auto", "numResults": max_results, "contents": {"highlights": True}},
                timeout=25,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Exa search failed for '{query}': {exc}")
            return []
        results = []
        for r in resp.json().get("results", []):
            if not r.get("url"):
                continue
            snippet = " ".join(r.get("highlights") or []) or (r.get("text") or "")
            results.append(
                WebResult(title=r.get("title") or r["url"], url=r["url"], snippet=snippet[:SNIPPET_CHARS], published_date=r.get("publishedDate"), image=r.get("image"))
            )
        return results
