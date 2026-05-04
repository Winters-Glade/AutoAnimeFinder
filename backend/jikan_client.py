"""
Jikan (MyAnimeList) API client — backup data source.

Jikan v4: https://docs.api.jikan.moe/
Rate limit: 30 req/min, 3 req/sec
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx

from models import Anime, UserAnime, UserAnimeStatus

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

JIKAN_API_URL = "https://api.jikan.moe/v4"
MAX_REQUESTS_PER_MINUTE = 30
MIN_INTERVAL = 60.0 / MAX_REQUESTS_PER_MINUTE  # ~2s between requests


# ──────────────────────────────────────────────
# Client
# ──────────────────────────────────────────────

class JikanClient:
    """Client for the Jikan (MAL) REST API."""

    def __init__(self, timeout: int = 30):
        self.base_url = JIKAN_API_URL
        self._last_request = 0.0
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def _rate_limited_get(self, path: str) -> Dict:
        """Make a rate-limited GET request to Jikan."""
        now = time.monotonic()
        since_last = now - self._last_request
        if since_last < MIN_INTERVAL:
            await asyncio.sleep(MIN_INTERVAL - since_last)
        self._last_request = time.monotonic()

        url = f"{self.base_url}{path}"
        response = await self._client.get(url)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning("Jikan rate limited. Waiting %ds...", retry_after)
            await asyncio.sleep(retry_after)
            return await self._rate_limited_get(path)

        response.raise_for_status()
        return response.json()

    async def fetch_user_anime_list(
        self, username: str
    ) -> List[UserAnime]:
        """Fetch a user's full anime list from MAL via Jikan."""
        all_entries: List[UserAnime] = []
        page = 1
        has_next = True
        max_404_retries = 3

        while has_next:
            # Jikan has a known caching issue where /animelist returns 404
            # for valid users. Retry with exponential backoff.
            for attempt in range(max_404_retries):
                try:
                    anime_data = await self._rate_limited_get(
                        f"/users/{username}/animelist?page={page}"
                    )
                    break  # Success
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404 and attempt < max_404_retries - 1:
                        wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                        logger.warning(
                            "Jikan animelist 404 on page %d (attempt %d/%d). "
                            "Waiting %ds before retry...",
                            page, attempt + 1, max_404_retries, wait
                        )
                        await asyncio.sleep(wait)
                    else:
                        raise  # Non-404 or exhausted retries

            entries = anime_data.get("data", [])
            for entry in entries:
                user_anime = self._parse_entry(entry)
                if user_anime:
                    all_entries.append(user_anime)

            has_next = bool(anime_data.get("pagination", {}).get("has_next_page", False))
            page += 1
            logger.info(
                "Jikan: fetched page %d (%d entries so far)",
                page - 1,
                len(all_entries),
            )

        return all_entries

    async def fetch_anime_detail(self, anime_id: int) -> Optional[Anime]:
        """Fetch detailed metadata for a single anime via Jikan."""
        data = await self._rate_limited_get(f"/anime/{anime_id}/full")
        entry = data.get("data")
        if not entry:
            return None
        return self._parse_anime(entry)

    # ──────────────────────────────────────────────
    # Parsing helpers
    # ──────────────────────────────────────────────

    def _parse_entry(self, entry: Dict) -> Optional[UserAnime]:
        """Parse a Jikan anime list entry into UserAnime."""
        anime_data = entry.get("anime", entry)  # Jikan v4 uses direct fields
        return UserAnime(
            anime=self._parse_anime(entry),
            score=entry.get("score"),
            progress=entry.get("episodes_watched", 0),
            status=self._parse_status(entry.get("watching_status")),
        )

    def _parse_anime(self, data: Dict) -> Anime:
        """Parse Jikan anime data into our Anime model."""
        title_obj = {
            "romaji": None,
            "english": data.get("title_english"),
            "native": data.get("title_japanese"),
        }
        # Try to get romaji from titles array
        for t in data.get("titles", []):
            if t.get("type") == "Default":
                title_obj["romaji"] = t.get("title")
            elif t.get("type") == "English" and not title_obj["english"]:
                title_obj["english"] = t.get("title")

        # Genres
        genres = [g["name"] for g in data.get("genres", [])]

        # Studios
        studios = []
        for s in data.get("studios", []):
            studios.append({
                "id": s.get("mal_id", 0),
                "name": s.get("name", ""),
                "isAnimationStudio": True,
            })

        # Demographics
        demographics = [d["name"] for d in data.get("demographics", [])]

        # Tags — Jikan doesn't have rich tags like AniList, so we leave this empty
        tags = []

        # Season
        season = data.get("season")
        if season:
            season = season.upper()

        return Anime(
            id=data.get("mal_id", 0),
            title=title_obj,
            genres=genres,
            tags=tags,
            studios=studios,
            demographics=demographics,
            season=season,
            seasonYear=data.get("year"),
            status=data.get("status", "").upper().replace(" ", "_") if data.get("status") else None,
            episodes=data.get("episodes"),
            duration=data.get("duration"),
            format=data.get("type", "").upper(),
            source=data.get("source", "").upper().replace(" ", "_"),
            synonyms=data.get("title_synonyms", []),
            meanScore=data.get("score"),
            averageScore=data.get("score"),
            popularity=data.get("popularity"),
            synopsis=data.get("synopsis"),
            description=data.get("synopsis"),
            coverImage={"large": data.get("images", {}).get("jpg", {}).get("large_image_url")},
            bannerImage=data.get("images", {}).get("jpg", {}).get("large_image_url"),
            startDate=data.get("aired", {}).get("from"),
            endDate=data.get("aired", {}).get("to"),
            nextAiringEpisode=None,
            relations=[],
            recommendations=[],
        )

    @staticmethod
    def _parse_status(status_int: Optional[int]) -> Optional[UserAnimeStatus]:
        """Convert Jikan numeric status to our enum."""
        mapping = {
            1: UserAnimeStatus.CURRENT,
            2: UserAnimeStatus.COMPLETED,
            3: UserAnimeStatus.PAUSED,
            4: UserAnimeStatus.DROPPED,
            6: UserAnimeStatus.PLANNING,
        }
        if status_int is None:
            return None
        return mapping.get(status_int)
