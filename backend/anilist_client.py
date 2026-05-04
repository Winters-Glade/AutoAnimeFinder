"""
AniList GraphQL API client.

Fetches user anime lists and full anime metadata from
https://graphql.anilist.co with pagination and rate-limit handling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx

from models import Anime, AnimeListResponse, UserAnime, UserAnimeStatus

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

ANILIST_API_URL = "https://graphql.anilist.co"
MAX_REQUESTS_PER_MINUTE = 90
REQUESTS_INTERVAL = 60.0 / MAX_REQUESTS_PER_MINUTE  # ~0.67s between requests
PAGE_SIZE = 50

# ──────────────────────────────────────────────
# GraphQL Queries
# ──────────────────────────────────────────────

ANIME_LIST_QUERY = """
query ($username: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      total
      currentPage
      lastPage
      hasNextPage
      perPage
    }
    mediaList(userName: $username, type: ANIME) {
      id
      userId
      status
      score(format: POINT_100)
      progress
      repeat
      startedAt { year month day }
      completedAt { year month day }
      media {
        id
        idMal
        title { romaji english native }
        genres
        tags {
          id
          name
          rank
          isGeneralSpoiler
          isMediaSpoiler
        }
        studios(isMain: true) {
          edges {
            node { id name isAnimationStudio }
          }
        }
        season
        seasonYear
        status
        episodes
        duration
        format
        source
        synonyms
        meanScore
        averageScore
        popularity
        description(asHtml: false)
        coverImage { large }
        bannerImage
        startDate { year month day }
        endDate { year month day }
        nextAiringEpisode { airingAt timeUntilAiring episode }
        relations {
          edges {
            relationType(version: 2)
            node {
              id
              title { romaji english }
              format
            }
          }
        }
        recommendations(page: 1, perPage: 10, sort: RATING_DESC) {
          edges {
            node {
              mediaRecommendation {
                id
                title { romaji english }
              }
              rating
            }
          }
        }
        externalLinks {
          site
          url
          type
        }
        streamingEpisodes {
          title
          url
          site
        }
      }
    }
  }
}
"""

ANIME_DETAIL_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { romaji english native }
    genres
    tags {
      id
      name
      rank
      isGeneralSpoiler
      isMediaSpoiler
    }
    studios(isMain: true) {
      edges {
        node { id name isAnimationStudio }
      }
    }
    season
    seasonYear
    status
    episodes
    duration
    format
    source
    synonyms
    meanScore
    averageScore
    popularity
    description(asHtml: false)
    coverImage { large }
    bannerImage
    startDate { year month day }
    endDate { year month day }
    nextAiringEpisode { airingAt timeUntilAiring episode }
    relations {
      edges {
        relationType(version: 2)
        node {
          id
          title { romaji english }
          format
        }
      }
    }
    recommendations(page: 1, perPage: 10, sort: RATING_DESC) {
      edges {
        node {
          mediaRecommendation {
            id
            title { romaji english }
          }
          rating
        }
      }
    }
  }
}
"""


# ──────────────────────────────────────────────
# Rate Limiter
# ──────────────────────────────────────────────

class RateLimiter:
    """Simple token-bucket rate limiter for API requests."""

    def __init__(self, max_per_minute: int = MAX_REQUESTS_PER_MINUTE):
        self.max_per_minute = max_per_minute
        self.min_interval = 60.0 / max_per_minute
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to stay within rate limits."""
        async with self._lock:
            now = time.monotonic()
            since_last = now - self._last_request
            if since_last < self.min_interval:
                wait = self.min_interval - since_last
                logger.debug("Rate limiter: sleeping %.2fs", wait)
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()


# ──────────────────────────────────────────────
# Client
# ──────────────────────────────────────────────

class AnilistClient:
    """Client for the AniList GraphQL API."""

    def __init__(self, timeout: int = 30):
        self.base_url = ANILIST_API_URL
        self.rate_limiter = RateLimiter()
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def _graphql_request(
        self, query: str, variables: Dict
    ) -> Dict:
        """Execute a GraphQL query with rate limiting."""
        await self.rate_limiter.acquire()
        try:
            response = await self._client.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )

            # Handle 429 rate limit before parsing JSON
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited (429). Waiting %ds...", retry_after)
                await asyncio.sleep(retry_after)
                return await self._graphql_request(query, variables)

            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_msg = data["errors"][0].get("message", "Unknown AniList error")
                raise Exception(f"AniList API error: {error_msg}")

            return data["data"]

    async def fetch_user_anime_list(
        self, username: str
    ) -> List[UserAnime]:
        """Fetch a user's complete anime list with pagination."""
        all_entries: List[UserAnime] = []
        page = 1
        has_next = True

        while has_next:
            data = await self._graphql_request(
                ANIME_LIST_QUERY,
                {"username": username, "page": page, "perPage": PAGE_SIZE},
            )
            page_data = data.get("Page", {})
            media_list = page_data.get("mediaList", [])
            page_info = page_data.get("pageInfo", {})

            for entry in media_list:
                user_anime = self._parse_media_list_entry(entry)
                if user_anime:
                    all_entries.append(user_anime)

            has_next = page_info.get("hasNextPage", False)
            page += 1
            logger.info(
                "Fetched page %d/%d (%d entries so far)",
                page - 1,
                page_info.get("lastPage", "?"),
                len(all_entries),
            )

        return all_entries

    async def fetch_anime_detail(self, anime_id: int) -> Optional[Anime]:
        """Fetch detailed metadata for a single anime."""
        data = await self._graphql_request(
            ANIME_DETAIL_QUERY, {"id": anime_id}
        )
        media = data.get("Media")
        if not media:
            return None
        return self._parse_anime(media)

    # ──────────────────────────────────────────────
    # Parsing helpers
    # ──────────────────────────────────────────────

    def _parse_media_list_entry(self, entry: Dict) -> Optional[UserAnime]:
        """Parse a mediaList entry from the GraphQL response."""
        if not entry or not entry.get("media"):
            return None

        media = entry["media"]
        return UserAnime(
            anime=self._parse_anime(media),
            userId=entry.get("userId"),
            score=entry.get("score"),
            progress=entry.get("progress"),
            status=self._parse_status(entry.get("status")),
            startedAt=entry.get("startedAt"),
            completedAt=entry.get("completedAt"),
            repeat=entry.get("repeat", 0),
        )

    def _parse_anime(self, media: Dict) -> Anime:
        """Parse a Media object from the GraphQL response."""
        # Extract studios from edges
        studios = []
        studio_edges = (media.get("studios") or {}).get("edges", [])
        for edge in studio_edges:
            node = edge.get("node", {})
            if node:
                studios.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "isAnimationStudio": node.get("isAnimationStudio", True),
                })

        # Extract relations
        relations = []
        relation_edges = (media.get("relations") or {}).get("edges", [])
        for edge in relation_edges:
            node = edge.get("node", {})
            if node:
                relations.append({
                    "id": node.get("id"),
                    "title": node.get("title", {}),
                    "relationType": edge.get("relationType", ""),
                    "format": node.get("format"),
                })

        # Extract recommendations
        recommendations = []
        rec_edges = (media.get("recommendations") or {}).get("edges", [])
        for edge in rec_edges:
            node = edge.get("node", {})
            rec_media = node.get("mediaRecommendation", {})
            if rec_media:
                recommendations.append({
                    "id": rec_media.get("id"),
                    "title": rec_media.get("title", {}),
                    "rating": node.get("rating"),
                })

        # Extract demographics — In AniList, demographics come from genres
        # that match known demographic categories
        demographics = [
            g for g in (media.get("genres") or [])
            if g.lower() in ("shounen", "shoujo", "seinen", "josei", "kids")
        ]

        return Anime(
            id=media["id"],
            idMal=media.get("idMal"),
            title=media.get("title", {}),
            genres=media.get("genres", []),
            tags=[{
                "id": t["id"],
                "name": t["name"],
                "rank": t.get("rank", 0),
                "isGeneralSpoiler": t.get("isGeneralSpoiler", False),
                "isMediaSpoiler": t.get("isMediaSpoiler", False),
            } for t in (media.get("tags") or [])],
            studios=studios,
            demographics=demographics,
            season=media.get("season"),
            seasonYear=media.get("seasonYear"),
            status=media.get("status"),
            episodes=media.get("episodes"),
            duration=media.get("duration"),
            format=media.get("format"),
            source=media.get("source"),
            synonyms=media.get("synonyms", []),
            meanScore=media.get("meanScore"),
            averageScore=media.get("averageScore"),
            popularity=media.get("popularity"),
            synopsis=media.get("description"),
            description=media.get("description"),
            coverImage=media.get("coverImage"),
            bannerImage=media.get("bannerImage"),
            startDate=media.get("startDate"),
            endDate=media.get("endDate"),
            nextAiringEpisode=media.get("nextAiringEpisode"),
            relations=relations,
            recommendations=recommendations,
            externalLinks=media.get("externalLinks", []),
            streamingEpisodes=media.get("streamingEpisodes", []),
        )

    @staticmethod
    def _parse_status(status_str: Optional[str]) -> Optional[UserAnimeStatus]:
        """Parse a status string into a UserAnimeStatus enum."""
        if not status_str:
            return None
        try:
            return UserAnimeStatus(status_str)
        except ValueError:
            return None
