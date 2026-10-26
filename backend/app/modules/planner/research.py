"""
Web research step: search first, then let the agents write from real results.

Results go into prompts as a numbered WEB_RESULTS block. Agents may only cite URLs from
that block; anything else is dropped by `keep_known_sources` (no invented links).
"""

import asyncio

from pydantic import BaseModel

from app.common.schemas import APIModel
from app.core.cache import Cache
from app.modules.trips.schemas import TripInputs
from app.providers.search import WebResult, WebSearchProvider

WEB_CACHE_TTL = 24 * 3600
PROMPT_SNIPPET_CHARS = 350
MAX_SIGHTS = 12
MAX_FOOD = 8


class Research(APIModel):
    sights: list[WebResult] = []
    food: list[WebResult] = []

    @property
    def empty(self) -> bool:
        return not (self.sights or self.food)

    @property
    def urls(self) -> set[str]:
        return {r.url for r in self.sights + self.food}


def _dedupe(results: list[WebResult], limit: int) -> list[WebResult]:
    seen: set[str] = set()
    out = []
    for r in results:
        if r.url not in seen:
            seen.add(r.url)
            out.append(r)
    return out[:limit]


async def _cached_search(search: WebSearchProvider, cache: Cache, query: str, n: int) -> list[WebResult]:
    async def fetch():
        return [r.model_dump() for r in await search.search(query, n)]

    data = await cache.get_or_set("web", [search.name, query.lower(), n], WEB_CACHE_TTL, fetch)
    return [WebResult.model_validate(r) for r in data or []]


async def gather_research(search: WebSearchProvider, cache: Cache, t: TripInputs) -> Research:
    if search.name == "none":
        return Research()
    dest = t.destination
    vibes = ", ".join(v.value for v in t.vibes) or "first-time visitors"
    diet = f" {', '.join(t.dietary)}" if t.dietary else ""
    sights_q = [f"best things to do in {dest} for {vibes}", f"hidden gems and local experiences in {dest}"]
    food_q = [f"best local restaurants and street food in {dest}{diet}"]
    results = await asyncio.gather(*(_cached_search(search, cache, q, 8) for q in sights_q + food_q), return_exceptions=True)
    ok = [r if isinstance(r, list) else [] for r in results]
    sights = _dedupe([r for group in ok[: len(sights_q)] for r in group], MAX_SIGHTS)
    food = _dedupe(ok[-1], MAX_FOOD)
    return Research(sights=sights, food=food)


def format_results(results: list[WebResult], label: str = "WEB_RESULTS") -> str:
    if not results:
        return ""
    lines = [f"{label}:"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.snippet[:PROMPT_SNIPPET_CHARS]}")
    lines.append(f"END_{label}")
    return "\n".join(lines)


def keep_known_sources(items: list[BaseModel], allowed: set[str]) -> int:
    """Null out any source_url the model invented. Returns how many were removed."""
    removed = 0
    for item in items:
        url = getattr(item, "source_url", None)
        if url and url not in allowed:
            item.source_url = None  # type: ignore[attr-defined]
            removed += 1
    return removed
