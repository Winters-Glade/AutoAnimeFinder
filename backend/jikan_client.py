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
            try:
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

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Jikan's animelist cache is broken for this user.
                    # Fall back to MAL's internal JSON endpoint.
                    logger.warning(
                        "Jikan animelist 404 for %s after retries. "
                        "Falling back to direct MAL fetch...",
                        username,
                    )
                    return await self._fetch_mal_direct(username)
                raise

        return all_entries

    async def _fetch_mal_direct(self, username: str) -> List[UserAnime]:
        """Fallback: fetch anime list directly from MAL's internal JSON endpoint.
        
        Used when Jikan's animelist cache is broken (returns 404 for valid users).
        The MAL endpoint paginates at 300 entries per request.
        """
        all_entries: List[UserAnime] = []
        offset = 0
        limit_per_page = 300
        page = 1

        while True:
            url = f"https://myanimelist.net/animelist/{username}/load.json?status=7&offset={offset}"
            logger.info("MAL direct: fetching page %d (offset=%d)", page, offset)

            response = await self._client.get(url)
            if response.status_code != 200:
                logger.error("MAL direct fetch failed: HTTP %d", response.status_code)
                response.raise_for_status()

            raw_entries = response.json()
            if not isinstance(raw_entries, list):
                logger.error("MAL direct fetch: unexpected response format")
                raise ValueError("Unexpected response format from MAL direct endpoint")

            if not raw_entries:
                break  # No more entries

            # Transform MAL JSON format to match Jikan's flat entry format
            # so _parse_entry can handle it.
            STATUS_MAP = {
                1: "watching",
                2: "completed",
                3: "on_hold",
                4: "dropped",
                6: "plan_to_watch",
            }

            parsed = 0
            failures = 0
            for raw in raw_entries:
                try:
                    # MAL media type → Format enum mapping
                    media_type = (raw.get("anime_media_type_string") or "").strip()
                    media_type_map = {
                        "TV": "TV",
                        "Movie": "MOVIE",
                        "OVA": "OVA",
                        "ONA": "ONA",
                        "Special": "SPECIAL",
                        "Music": "MUSIC",
                    }
                    fmt = media_type_map.get(media_type, "TV")

                    # Build a Jikan-compatible entry dict
                    # MAL scores are 1-10, normalize to 0-100
                    mal_score = raw.get("score", 0)
                    normalized_score = mal_score * 10 if mal_score else 0

                    # Parse airing status: 1=currently_airing, 2=finished, 3=not_yet_aired
                    airing_status = raw.get("anime_airing_status")
                    status_map = {1: "CURRENTLY_AIRING", 2: "FINISHED", 3: "NOT_YET_AIRED"}
                    status_str = status_map.get(airing_status) if airing_status else None

                    # Parse start date (MM-DD-YY) to extract season and year
                    season = None
                    year = None
                    aired_from = None
                    aired_to = None
                    start_date_str = raw.get("anime_start_date_string")
                    end_date_str = raw.get("anime_end_date_string")
                    if start_date_str:
                        try:
                            parts = start_date_str.split("-")
                            if len(parts) == 3:
                                month = int(parts[0])
                                day = int(parts[1])
                                yr = int(parts[2])
                                # Handle 2-digit years
                                if yr < 100:
                                    yr += 2000
                                year = yr
                                # Determine season from month
                                if month in (12, 1, 2):
                                    season = "WINTER"
                                elif month in (3, 4, 5):
                                    season = "SPRING"
                                elif month in (6, 7, 8):
                                    season = "SUMMER"
                                else:
                                    season = "FALL"
                                aired_from = {"year": year, "month": month, "day": day}
                        except (ValueError, IndexError):
                            pass
                    if end_date_str:
                        try:
                            parts = end_date_str.split("-")
                            if len(parts) == 3:
                                aired_to = {"year": int(parts[2]) + 2000 if int(parts[2]) < 100 else int(parts[2]),
                                            "month": int(parts[0]), "day": int(parts[1])}
                        except (ValueError, IndexError):
                            pass

                    entry = {
                        "mal_id": raw.get("anime_id", 0),
                        "title": raw.get("anime_title", ""),
                        "title_english": raw.get("anime_title_eng", ""),
                        "title_japanese": raw.get("anime_title_jp", ""),
                        "type": fmt,
                        "source": "OTHER",
                        "season": season,
                        "year": year,
                        "status": status_str,
                        "aired": {"from": aired_from, "to": aired_to},
                        "episodes": raw.get("anime_num_episodes", 0),
                        "duration": None,
                        "score": normalized_score,
                        "episodes_watched": raw.get("num_watched_episodes", 0),
                        "watching_status": raw.get("status", 1),
                        "genres": raw.get("genres", []),
                        "demographics": raw.get("demographics", []),
                        "synopsis": raw.get("anime_synopsis") or "",
                        "popularity": raw.get("anime_popularity"),
                        "url": f"https://myanimelist.net/anime/{raw.get('anime_id', 0)}",
                        "images": {
                            "jpg": {
                                "image_url": raw.get("anime_image_path", ""),
                                "large_image_url": raw.get("anime_image_path", ""),
                            },
                        },
                        "titles": [
                            {"type": "Default", "title": raw.get("anime_title", "")},
                        ],
                    }
                    # Add English title to titles array if different
                    eng_title = raw.get("anime_title_eng", "")
                    if eng_title and eng_title != raw.get("anime_title", ""):
                        entry["titles"].append({"type": "English", "title": eng_title})

                    user_anime = self._parse_entry(entry)
                    if user_anime:
                        all_entries.append(user_anime)
                        parsed += 1
                except Exception as e:
                    logger.warning("MAL direct: failed to parse entry: %s", e)
                    failures += 1
                    continue

            logger.info(
                "MAL direct: page %d done — parsed=%d failures=%d total=%d",
                page, parsed, failures, len(all_entries),
            )

            # If we got fewer entries than the limit, we've reached the end
            if len(raw_entries) < limit_per_page:
                break

            offset += limit_per_page
            page += 1

        logger.info(
            "MAL direct: finished — %d total entries for %s",
            len(all_entries), username,
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

    @staticmethod
    def _normalize_status(status: Optional[str]) -> Optional[str]:
        """Convert Jikan/MAL airing status to AnimeStatus enum value."""
        if not status:
            return None
        upper = status.upper().replace(" ", "_")
        STATUS_MAP = {
            "CURRENTLY_AIRING": "RELEASING",
            "FINISHED_AIRING": "FINISHED",
            "FINISHED": "FINISHED",
            "NOT_YET_AIRED": "NOT_YET_RELEASED",
            "NOT_YET_RELEASED": "NOT_YET_RELEASED",
            "CANCELLED": "CANCELLED",
            "HIATUS": "HIATUS",
        }
        return STATUS_MAP.get(upper, upper)

    @staticmethod
    def _parse_jikan_duration(duration: Any) -> Optional[int]:
        """Parse Jikan duration string like '24 min per ep' to minutes."""
        if duration is None:
            return None
        if isinstance(duration, (int, float)):
            return int(duration)
        if isinstance(duration, str):
            import re
            match = re.search(r'(\d+)', duration)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _parse_jikan_score(score: Any) -> Optional[int]:
        """Convert Jikan score (0-10 float) to 0-100 int for Anime model."""
        if score is None:
            return None
        try:
            s = float(score)
            if s <= 10:
                return int(s * 10)
            return int(s)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_jikan_date(date_val: Any) -> Optional[dict]:
        """Parse Jikan date string like '2019-01-11T00:00:00+00:00' to FuzzyDate dict."""
        if not date_val:
            return None
        if isinstance(date_val, dict):
            return date_val
        if isinstance(date_val, str):
            import re
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_val)
            if match:
                return {
                    "year": int(match.group(1)),
                    "month": int(match.group(2)),
                    "day": int(match.group(3)),
                }
        return None

    def _parse_entry(self, entry: Dict) -> Optional[UserAnime]:
        """Parse a Jikan anime list entry into UserAnime."""
        anime_data = entry.get("anime", entry)  # Jikan v4 uses nested "anime" object
        raw_score = entry.get("score", 0) or 0
        # MAL scores are 0-10, normalize to 0-100
        if raw_score <= 10:
            normalized_score = raw_score * 10
        else:
            normalized_score = raw_score
        return UserAnime(
            anime=self._parse_anime(anime_data),
            score=normalized_score,
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
            status=self._normalize_status(data.get("status")),
            episodes=data.get("episodes"),
            duration=self._parse_jikan_duration(data.get("duration")),
            format=data.get("type", "").upper(),
            source=data.get("source", "").upper().replace(" ", "_"),
            synonyms=data.get("title_synonyms", []),
            meanScore=self._parse_jikan_score(data.get("score")),
            averageScore=self._parse_jikan_score(data.get("score")),
            popularity=data.get("popularity"),
            synopsis=data.get("synopsis"),
            description=data.get("synopsis"),
            coverImage={"large": data.get("images", {}).get("jpg", {}).get("large_image_url")},
            bannerImage=data.get("images", {}).get("jpg", {}).get("large_image_url"),
            startDate=self._parse_jikan_date(data.get("aired", {}).get("from")),
            endDate=self._parse_jikan_date(data.get("aired", {}).get("to")),
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
