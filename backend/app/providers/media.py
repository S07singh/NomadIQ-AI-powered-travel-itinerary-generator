"""
Images, videos and short destination knowledge.

Defaults are free and key-less (Wikipedia/Wikimedia for images + summaries,
YouTube search links for videos) so the app shows visuals from day one.
Unsplash / Pexels / YouTube Data API can be switched on with keys.
"""

from abc import ABC, abstractmethod
from urllib.parse import quote, quote_plus

import httpx
from loguru import logger

from app.common.schemas import APIModel, MediaImage, VideoLink

USER_AGENT = "NomadIQ/2.0 (travel planner; contact: support@nomadiq.app)"


class PlaceSummary(APIModel):
    title: str
    summary: str
    url: str | None = None
    image: MediaImage | None = None


def slugify(text: str) -> str:
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in text).split())


def maps_url(*parts: str) -> str:
    """Universal Google Maps link: opens the app on iOS/Android, the website on desktop."""
    query = ", ".join(p for p in parts if p)
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


# ─── Images ────────────────────────────────────────────────────────

class ImageProvider(ABC):
    name = "base"

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[MediaImage]: ...


class MockImageProvider(ImageProvider):
    name = "mock"

    async def search(self, query: str, limit: int = 5) -> list[MediaImage]:
        slug = slugify(query) or "travel"
        return [
            MediaImage(
                url=f"https://picsum.photos/seed/{slug}-{i}/1200/800",
                thumbnail_url=f"https://picsum.photos/seed/{slug}-{i}/400/300",
                width=1200,
                height=800,
                alt=query,
                source="mock",
            )
            for i in range(limit)
        ]


DISPLAY_WIDTH = 1280
THUMB_WIDTH = 500  # Wikimedia only serves standard widths (e.g. 250, 330, 500, 960, 1280); 480 returns HTTP 400


def small_variant(url: str) -> str:
    """Wikimedia thumbnail URLs embed the width ("/1280px-Name.jpg"); ask for a smaller rendition."""
    return url.replace(f"/{DISPLAY_WIDTH}px-", f"/{THUMB_WIDTH}px-")


NON_PHOTO_HINTS = ("map", "locator", "flag", "logo", "coat_of_arms", "emblem", "seal_of", "diagram", "chart", "signature", ".svg")


def is_photo(url: str) -> bool:
    """Skip maps, flags, logos and other non-photographs that Wikipedia uses as page images."""
    name = url.rsplit("/", 1)[-1].lower()
    return not any(hint in name for hint in NON_PHOTO_HINTS)


class WikipediaImageProvider(ImageProvider):
    """Sized thumbnails (not originals, which are often several MB) keep pages fast."""

    name = "wikipedia"

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def search(self, query: str, limit: int = 5) -> list[MediaImage]:
        params = {
            "action": "query", "format": "json", "formatversion": "2",
            "generator": "search", "gsrsearch": query, "gsrlimit": str(max(limit, 3)),
            "prop": "pageimages|info", "piprop": "thumbnail", "pithumbsize": str(DISPLAY_WIDTH), "inprop": "url",
        }
        try:
            resp = await self.http.get("https://en.wikipedia.org/w/api.php", params=params, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Wikipedia image search failed for '{query}': {exc}")
            return []
        pages = sorted(resp.json().get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
        images = []
        for page in pages:
            thumb = page.get("thumbnail")
            if not thumb or not is_photo(thumb["source"]):
                continue
            images.append(
                MediaImage(
                    url=thumb["source"],
                    thumbnail_url=small_variant(thumb["source"]),
                    width=thumb.get("width"),
                    height=thumb.get("height"),
                    alt=page.get("title", query),
                    attribution="Wikimedia Commons",
                    source="wikipedia",
                    source_url=page.get("fullurl"),
                )
            )
        return images[:limit]


class UnsplashImageProvider(ImageProvider):
    name = "unsplash"

    def __init__(self, http: httpx.AsyncClient, access_key: str):
        self.http, self.key = http, access_key

    async def search(self, query: str, limit: int = 5) -> list[MediaImage]:
        try:
            resp = await self.http.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": limit, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {self.key}", "Accept-Version": "v1"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Unsplash search failed for '{query}': {exc}")
            return []
        return [
            MediaImage(
                url=r["urls"]["regular"],
                thumbnail_url=r["urls"].get("small"),
                width=r.get("width"),
                height=r.get("height"),
                alt=r.get("alt_description") or query,
                attribution=f"Photo by {r['user']['name']} on Unsplash",
                source="unsplash",
                source_url=r["links"]["html"],
            )
            for r in resp.json().get("results", [])
        ]


class PexelsImageProvider(ImageProvider):
    name = "pexels"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        self.http, self.key = http, api_key

    async def search(self, query: str, limit: int = 5) -> list[MediaImage]:
        try:
            resp = await self.http.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": limit, "orientation": "landscape"},
                headers={"Authorization": self.key},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Pexels search failed for '{query}': {exc}")
            return []
        return [
            MediaImage(
                url=p["src"]["large"],
                thumbnail_url=p["src"].get("medium"),
                width=p.get("width"),
                height=p.get("height"),
                alt=p.get("alt") or query,
                attribution=f"Photo by {p['photographer']} on Pexels",
                source="pexels",
                source_url=p.get("url"),
            )
            for p in resp.json().get("photos", [])
        ]


# ─── Videos ────────────────────────────────────────────────────────

class VideoProvider(ABC):
    name = "base"

    @abstractmethod
    async def search(self, query: str, limit: int = 3) -> list[VideoLink]: ...


class YouTubeLinkProvider(VideoProvider):
    """Zero-latency, zero-quota: a YouTube search link the app opens directly."""

    name = "youtube_link"

    async def search(self, query: str, limit: int = 3) -> list[VideoLink]:
        return [VideoLink(title=f"{query} — videos on YouTube", url=f"https://www.youtube.com/results?search_query={quote_plus(query)}", source="youtube_link")]


class MockVideoProvider(YouTubeLinkProvider):
    name = "mock"


class YouTubeDataProvider(VideoProvider):
    """YouTube Data API v3. search.list costs 100 quota units (10k/day default) — always cache results."""

    name = "youtube"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        self.http, self.key = http, api_key

    async def search(self, query: str, limit: int = 3) -> list[VideoLink]:
        try:
            resp = await self.http.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": query, "type": "video", "maxResults": limit, "videoEmbeddable": "true", "safeSearch": "moderate", "key": self.key},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"YouTube search failed for '{query}': {exc}")
            return await YouTubeLinkProvider().search(query, limit)
        return [
            VideoLink(
                title=item["snippet"]["title"],
                url=f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                thumbnail_url=item["snippet"]["thumbnails"].get("medium", {}).get("url"),
                channel=item["snippet"].get("channelTitle"),
                source="youtube",
            )
            for item in resp.json().get("items", [])
            if item.get("id", {}).get("videoId")
        ]


# ─── Knowledge (short destination summaries) ──────────────────────

class KnowledgeProvider(ABC):
    @abstractmethod
    async def summary(self, query: str) -> PlaceSummary | None: ...


class MockKnowledgeProvider(KnowledgeProvider):
    async def summary(self, query: str) -> PlaceSummary | None:
        return PlaceSummary(title=query.title(), summary=f"{query.title()} is a popular travel destination known for its culture, food and sights.")


class WikipediaKnowledgeProvider(KnowledgeProvider):
    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def summary(self, query: str) -> PlaceSummary | None:
        title = quote(query.strip().replace(" ", "_"))
        try:
            resp = await self.http.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                params={"redirect": "true"},
                headers={"User-Agent": USER_AGENT},
            )
        except httpx.HTTPError as exc:
            logger.warning(f"Wikipedia summary failed for '{query}': {exc}")
            return None
        if resp.status_code != 200:
            return None
        data = resp.json()
        image = data.get("originalimage") or data.get("thumbnail")
        return PlaceSummary(
            title=data.get("title", query),
            summary=data.get("extract", ""),
            url=(data.get("content_urls") or {}).get("desktop", {}).get("page"),
            image=MediaImage(url=image["source"], width=image.get("width"), height=image.get("height"), alt=data.get("title", query), attribution="Wikimedia Commons", source="wikipedia") if image else None,
        )
