"""
FastAPI application for anime-soul-whisper recommendation engine.

Endpoints:
- POST /api/anilist/fetch       — Fetch user's AniList data
- POST /api/jikan/fetch         — Fetch user's MAL data via Jikan
- GET  /api/profile/taste       — Compute and return taste profile
- POST /api/recommendations/mood    — Mood-based recommendations
- POST /api/recommendations/direct  — Direct filter recommendations
- GET  /api/anime/{id}          — Full anime details
- GET  /api/search/history      — List saved searches
- POST /api/search/history      — Save a search
- GET  /api/search/history/{id} — Load a specific saved search
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from models import (
    AnilistFetchRequest,
    Anime,
    AnimeListResponse,
    DirectRecommendationRequest,
    JikanFetchRequest,
    MoodRecommendationRequest,
    Recommendation,
    RecommendationResponse,
    SearchHistoryEntry,
    SearchHistoryList,
    TasteProfile,
    UserAnime,
)

from anilist_client import AnilistClient
from jikan_client import JikanClient
from taste_profile import TasteProfileEngine
from recommender import content_based, mood_based, direct_filters

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="AutoAnimeFinder — Recommendation Engine",
    description="AI-powered anime recommendation engine with taste profiling",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Serve built frontend as static files
# ──────────────────────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
FRONTEND_INDEX = os.path.join(FRONTEND_DIST, "index.html")

# Serve assets (JS, CSS, images) from the built frontend
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend_assets")


@app.get("/favicon.svg")
async def favicon():
    fpath = os.path.join(FRONTEND_DIST, "favicon.svg")
    if os.path.isfile(fpath):
        return FileResponse(fpath, media_type="image/svg+xml")
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# ──────────────────────────────────────────────
# Cache directory
# ──────────────────────────────────────────────

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

SEARCH_HISTORY_FILE = os.path.join(CACHE_DIR, "search_history.json")


def _cache_path(key: str) -> str:
    """Return a safe file path for a cache key."""
    safe = key.replace("/", "_").replace(" ", "_").lower()
    return os.path.join(CACHE_DIR, f"{safe}.json")


def _load_cache(key: str, max_age_secs: int = 3600) -> Optional[dict]:
    """Load cached data if it exists and is fresh enough."""
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        age = time.time() - os.path.getmtime(path)
        if age > max_age_secs:
            return None
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(key: str, data: dict) -> None:
    """Save data to the cache."""
    path = _cache_path(key)
    try:
        with open(path, "w") as f:
            json.dump(data, f, default=str, indent=2)
    except OSError as e:
        logger.warning("Failed to write cache %s: %s", key, e)


def _anime_to_cache_dict(anime: Anime) -> dict:
    """Convert an Anime model to a JSON-serializable dict."""
    return json.loads(anime.model_dump_json())


def _user_anime_to_cache_dict(ua: UserAnime) -> dict:
    """Convert a UserAnime to a JSON-serializable dict."""
    return json.loads(ua.model_dump_json())


# ──────────────────────────────────────────────
# Search history helpers
# ──────────────────────────────────────────────


def _load_search_history() -> List[dict]:
    """Load all search history entries from the JSON file."""
    if not os.path.exists(SEARCH_HISTORY_FILE):
        return []
    try:
        with open(SEARCH_HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_search_history(entries: List[dict]) -> None:
    """Save search history entries to the JSON file."""
    try:
        with open(SEARCH_HISTORY_FILE, "w") as f:
            json.dump(entries, f, default=str, indent=2)
    except OSError as e:
        logger.warning("Failed to save search history: %s", e)


def _get_next_id(entries: List[dict]) -> int:
    """Get the next available ID for a new history entry."""
    if not entries:
        return 1
    return max(e.get("id", 0) for e in entries) + 1


# ──────────────────────────────────────────────
# Client lifecycle
# ──────────────────────────────────────────────

_anilist_client: Optional[AnilistClient] = None
_jikan_client: Optional[JikanClient] = None


def get_anilist_client() -> AnilistClient:
    global _anilist_client
    if _anilist_client is None:
        _anilist_client = AnilistClient()
    return _anilist_client


def get_jikan_client() -> JikanClient:
    global _jikan_client
    if _jikan_client is None:
        _jikan_client = JikanClient()
    return _jikan_client


@app.on_event("shutdown")
async def shutdown():
    global _anilist_client, _jikan_client
    if _anilist_client:
        await _anilist_client.close()
    if _jikan_client:
        await _jikan_client.close()


# ──────────────────────────────────────────────
# In-memory anime catalog cache
# ──────────────────────────────────────────────

# We cache fetched anime so recommendations can work without re-fetching
_anime_catalog: Dict[int, Anime] = {}


def _get_all_anime_from_catalog() -> List[Anime]:
    """Get all anime from the in-memory catalog."""
    return list(_anime_catalog.values())


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── AniList fetch ──────────────────────────────


@app.post("/api/anilist/fetch", response_model=AnimeListResponse)
async def fetch_anilist(request: AnilistFetchRequest):
    """Fetch a user's anime list from AniList."""
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    cache_key = f"anilist_user_{username}"
    cached = _load_cache(cache_key, max_age_secs=300)  # 5 min cache
    if cached:
        logger.info("Returning cached AniList data for %s", username)
        return AnimeListResponse(**cached)

    try:
        client = get_anilist_client()
        user_anime_list = await client.fetch_user_anime_list(username)
    except Exception as e:
        logger.error("AniList fetch failed for %s: %s", username, e)
        raise HTTPException(status_code=502, detail=f"AniList API error: {e}")

    # Add to catalog
    for ua in user_anime_list:
        _anime_catalog[ua.anime.id] = ua.anime

    response = AnimeListResponse(
        username=username,
        source="anilist",
        animeList=user_anime_list,
        totalCount=len(user_anime_list),
        fetchedAt=datetime.utcnow(),
    )

    # Cache the response
    _save_cache(
        cache_key,
        {
            "username": username,
            "source": "anilist",
            "animeList": [_user_anime_to_cache_dict(ua) for ua in user_anime_list],
            "totalCount": len(user_anime_list),
            "fetchedAt": datetime.utcnow().isoformat(),
        },
    )

    return response


# ── Jikan fetch ────────────────────────────────


@app.post("/api/jikan/fetch", response_model=AnimeListResponse)
async def fetch_jikan(request: JikanFetchRequest):
    """Fetch a user's anime list from MAL via Jikan."""
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    cache_key = f"jikan_user_{username}"
    cached = _load_cache(cache_key, max_age_secs=300)
    if cached:
        logger.info("Returning cached Jikan data for %s", username)
        return AnimeListResponse(**cached)

    try:
        client = get_jikan_client()
        user_anime_list = await client.fetch_user_anime_list(username)
    except Exception as e:
        logger.error("Jikan fetch failed for %s: %s", username, e)
        raise HTTPException(status_code=502, detail=f"Jikan API error: {e}")

    # Add to catalog
    for ua in user_anime_list:
        _anime_catalog[ua.anime.id] = ua.anime

    response = AnimeListResponse(
        username=username,
        source="mal",
        animeList=user_anime_list,
        totalCount=len(user_anime_list),
        fetchedAt=datetime.utcnow(),
    )

    _save_cache(
        cache_key,
        {
            "username": username,
            "source": "mal",
            "animeList": [_user_anime_to_cache_dict(ua) for ua in user_anime_list],
            "totalCount": len(user_anime_list),
            "fetchedAt": datetime.utcnow().isoformat(),
        },
    )

    return response


# ── Taste Profile ──────────────────────────────


@app.get("/api/profile/taste", response_model=TasteProfile)
async def get_taste_profile(
    username: str = Query(..., description="AniList or MAL username"),
    source: str = Query("anilist", description="Data source: 'anilist' or 'mal'"),
):
    """Compute and return a taste profile for the given user."""
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    # Check if we have cached data
    cache_key = f"{source}_user_{username}"
    cached = _load_cache(cache_key, max_age_secs=300)
    if cached:
        # Parse cached UserAnime list
        user_anime_list = [UserAnime(**ua) for ua in cached.get("animeList", [])]
    else:
        # Fetch fresh data
        try:
            if source == "anilist":
                client = get_anilist_client()
            else:
                client = get_jikan_client()
            user_anime_list = await client.fetch_user_anime_list(username)
        except Exception as e:
            logger.error("Fetch failed for taste profile: %s", e)
            raise HTTPException(status_code=502, detail=f"API error: {e}")

        # Add to catalog
        for ua in user_anime_list:
            _anime_catalog[ua.anime.id] = ua.anime

        # Cache it
        _save_cache(
            cache_key,
            {
                "username": username,
                "source": source,
                "animeList": [_user_anime_to_cache_dict(ua) for ua in user_anime_list],
                "totalCount": len(user_anime_list),
                "fetchedAt": datetime.utcnow().isoformat(),
            },
        )

    if not user_anime_list:
        raise HTTPException(status_code=404, detail=f"No anime list found for {username} on {source}")

    engine = TasteProfileEngine(username=username, anime_list=user_anime_list)
    profile = engine.compute()

    return profile


# ── Anime Details ──────────────────────────────


@app.get("/api/anime/{anime_id}", response_model=Anime)
async def get_anime_details(anime_id: int):
    """Fetch full details for a specific anime by ID."""
    # Check in-memory catalog first
    if anime_id in _anime_catalog:
        return _anime_catalog[anime_id]

    # Try cache
    cache_key = f"anime_detail_{anime_id}"
    cached = _load_cache(cache_key, max_age_secs=86400)  # 24h cache
    if cached:
        anime = Anime(**cached)
        _anime_catalog[anime_id] = anime
        return anime

    # Fetch from AniList
    try:
        client = get_anilist_client()
        anime = await client.fetch_anime_detail(anime_id)
    except Exception as e:
        logger.error("Failed to fetch anime %d: %s", anime_id, e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch anime details: {e}")

    if not anime:
        raise HTTPException(status_code=404, detail=f"Anime #{anime_id} not found")

    _anime_catalog[anime_id] = anime
    _save_cache(cache_key, _anime_to_cache_dict(anime))

    return anime


# ── Mood-based recommendations ─────────────────


@app.post("/api/recommendations/mood", response_model=RecommendationResponse)
async def get_mood_recommendations(request: MoodRecommendationRequest):
    """Get AI-powered mood-based anime recommendations."""
    # Build the candidate pool from the catalog
    all_anime = _get_all_anime_from_catalog()
    if not all_anime:
        # If catalog is empty, we need the user to fetch their list first
        raise HTTPException(
            status_code=400,
            detail="No anime catalog available. Fetch user data first via /api/anilist/fetch or /api/jikan/fetch.",
        )

    filters = {
        "brainPower": request.brainPower,
        "timeCommitment": request.timeCommitment,
        "moodIntent": request.moodIntent,
        "avoidList": request.avoidList or [],
        "excludeList": request.excludeList or [],
    }

    try:
        recommendations = await mood_based(
            mood_query=request.moodQuery,
            filters=filters,
            all_anime=all_anime,
        )
    except Exception as e:
        logger.error("Mood recommendation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Recommendation engine error: {e}")

    return RecommendationResponse(
        recommendations=recommendations,
        source="ai_mood",
        totalMatches=len(recommendations),
    )


# ── Direct filter recommendations ──────────────


@app.post("/api/recommendations/direct", response_model=RecommendationResponse)
async def get_direct_recommendations(request: DirectRecommendationRequest):
    """Get filter-based anime recommendations (no AI mood)."""
    all_anime = _get_all_anime_from_catalog()
    if not all_anime:
        raise HTTPException(
            status_code=400,
            detail="No anime catalog available. Fetch user data first via /api/anilist/fetch or /api/jikan/fetch.",
        )

    filters = {
        "genres": request.genres or [],
        "timeCommitment": request.timeCommitment,
        "brainPower": request.brainPower,
        "mood": request.mood,
        "avoidList": request.avoidList or [],
        "excludeList": request.excludeList or [],
        "limit": request.limit,
    }

    try:
        recommendations = await direct_filters(filters=filters, all_anime=all_anime)
    except Exception as e:
        logger.error("Direct recommendation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Recommendation engine error: {e}")

    return RecommendationResponse(
        recommendations=recommendations,
        source="direct",
        totalMatches=len(recommendations),
    )


# ── Recommendation (simple content-based) ──────


@app.post("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: dict = {}):
    """
    Simple content-based recommendations.

    Expects JSON body with:
    - username (str): the user to get recommendations for
    - source (str, optional): 'anilist' (default) or 'mal'
    - limit (int, optional): max results (default 20)
    """
    username = request.get("username", "")
    source = request.get("source", "anilist")
    limit = request.get("limit", 20)

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    # Get user's anime list
    cache_key = f"{source}_user_{username}"
    cached = _load_cache(cache_key, max_age_secs=300)
    if cached:
        user_anime_list = [UserAnime(**ua) for ua in cached.get("animeList", [])]
        # Also rebuild catalog from cache
        for ua in user_anime_list:
            _anime_catalog[ua.anime.id] = ua.anime
    else:
        try:
            if source == "anilist":
                client = get_anilist_client()
            else:
                client = get_jikan_client()
            user_anime_list = await client.fetch_user_anime_list(username)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"API error: {e}")

        for ua in user_anime_list:
            _anime_catalog[ua.anime.id] = ua.anime

        _save_cache(
            cache_key,
            {
                "username": username,
                "source": source,
                "animeList": [_user_anime_to_cache_dict(ua) for ua in user_anime_list],
                "totalCount": len(user_anime_list),
                "fetchedAt": datetime.utcnow().isoformat(),
            },
        )

    all_anime = _get_all_anime_from_catalog()
    if not user_anime_list or not all_anime:
        raise HTTPException(status_code=404, detail=f"No anime data found for {username}")

    try:
        recommendations = await content_based(user_anime_list, all_anime)
    except Exception as e:
        logger.error("Content-based recommendation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Recommendation error: {e}")

    # Apply limit
    recommendations = recommendations[:limit]

    return RecommendationResponse(
        recommendations=recommendations,
        source="content_based",
        totalMatches=len(recommendations),
    )


# ── Search History ─────────────────────────────


@app.get("/api/search/history", response_model=SearchHistoryList)
async def list_search_history():
    """List all saved searches."""
    entries = _load_search_history()
    return SearchHistoryList(entries=[SearchHistoryEntry(**e) for e in entries])


@app.post("/api/search/history", response_model=SearchHistoryEntry)
async def save_search(entry: SearchHistoryEntry):
    """Save a search to history."""
    entries = _load_search_history()
    entry.id = _get_next_id(entries)
    entry.created_at = datetime.utcnow()
    entries.append(json.loads(entry.model_dump_json()))
    _save_search_history(entries)
    return entry


@app.get("/api/search/history/{entry_id}", response_model=SearchHistoryEntry)
async def get_search_history_entry(entry_id: int):
    """Load a specific saved search by ID."""
    entries = _load_search_history()
    for e in entries:
        if e.get("id") == entry_id:
            return SearchHistoryEntry(**e)
    raise HTTPException(status_code=404, detail=f"Search history entry #{entry_id} not found")


# ──────────────────────────────────────────────
# SPA catch-all — serve index.html for all non-API paths
# ──────────────────────────────────────────────

if os.path.isfile(FRONTEND_INDEX):

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Don't catch /api/ paths — let them return proper 404
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return FileResponse(FRONTEND_INDEX)

# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
