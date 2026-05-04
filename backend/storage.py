"""
Storage module — SQLite-backed cache and search history persistence.

Provides:
- Anime metadata cache (24h TTL)
- User anime list cache (1h TTL)
- Taste profile cache (1h TTL)
- Search history storage (permanent)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models import Anime, SearchHistoryEntry, TasteProfile, UserAnime

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Database setup
# ──────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "anime_soul_whisper.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS anime_cache (
    id INTEGER PRIMARY KEY,
    data TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_list_cache (
    username TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'anilist',
    data TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, source)
);

CREATE TABLE IF NOT EXISTS taste_profile_cache (
    username TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'anilist',
    data TEXT NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, source)
);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    query TEXT DEFAULT '',
    filters TEXT DEFAULT '{}',
    results TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_history_username ON search_history(username);
CREATE INDEX IF NOT EXISTS idx_search_history_created ON search_history(created_at);
"""


# ──────────────────────────────────────────────
# Storage class
# ──────────────────────────────────────────────

class Storage:
    """SQLite-based persistence layer."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        yield self._local.conn

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_conn() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    # ──────────────────────────────────────────
    # Anime cache
    # ──────────────────────────────────────────

    def get_cached_anime(self, anime_id: int, max_age: timedelta = timedelta(hours=24)) -> Optional[Anime]:
        """Get cached anime metadata if not expired."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data, fetched_at FROM anime_cache WHERE id = ?",
                (anime_id,),
            ).fetchone()
            if row:
                fetched = datetime.fromisoformat(row["fetched_at"])
                if datetime.utcnow() - fetched < max_age:
                    try:
                        data = json.loads(row["data"])
                        return Anime(**data)
                    except Exception as e:
                        logger.warning("Failed to parse cached anime %d: %s", anime_id, e)
        return None

    def cache_anime(self, anime: Anime):
        """Cache anime metadata."""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO anime_cache (id, data, fetched_at)
                   VALUES (?, ?, ?)""",
                (anime.id, anime.model_dump_json(), datetime.utcnow().isoformat()),
            )
            conn.commit()

    # ──────────────────────────────────────────
    # User list cache
    # ──────────────────────────────────────────

    def get_cached_user_list(self, username: str, source: str = "anilist",
                             max_age: timedelta = timedelta(hours=1)) -> Optional[List[UserAnime]]:
        """Get cached user anime list if not expired."""
        key = username.lower()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data, fetched_at FROM user_list_cache WHERE username = ? AND source = ?",
                (key, source),
            ).fetchone()
            if row:
                fetched = datetime.fromisoformat(row["fetched_at"])
                if datetime.utcnow() - fetched < max_age:
                    try:
                        data = json.loads(row["data"])
                        return [UserAnime(**ua) for ua in data]
                    except Exception as e:
                        logger.warning("Failed to parse cached user list: %s", e)
        return None

    def cache_user_list(self, username: str, anime_list: List[UserAnime], source: str = "anilist"):
        """Cache a user's anime list."""
        key = username.lower()
        data = [ua.model_dump() for ua in anime_list]
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO user_list_cache (username, source, data, fetched_at)
                   VALUES (?, ?, ?, ?)""",
                (key, source, json.dumps(data), datetime.utcnow().isoformat()),
            )
            conn.commit()

    # ──────────────────────────────────────────
    # Taste profile cache
    # ──────────────────────────────────────────

    def get_cached_taste_profile(self, username: str, source: str = "anilist",
                                  max_age: timedelta = timedelta(hours=1)) -> Optional[TasteProfile]:
        """Get cached taste profile if not expired."""
        key = username.lower()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data, computed_at FROM taste_profile_cache WHERE username = ? AND source = ?",
                (key, source),
            ).fetchone()
            if row:
                computed = datetime.fromisoformat(row["computed_at"])
                if datetime.utcnow() - computed < max_age:
                    try:
                        data = json.loads(row["data"])
                        return TasteProfile(**data)
                    except Exception as e:
                        logger.warning("Failed to parse cached taste profile: %s", e)
        return None

    def cache_taste_profile(self, username: str, profile: TasteProfile, source: str = "anilist"):
        """Cache a taste profile."""
        key = username.lower()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO taste_profile_cache (username, source, data, computed_at)
                   VALUES (?, ?, ?, ?)""",
                (key, source, profile.model_dump_json(), datetime.utcnow().isoformat()),
            )
            conn.commit()

    # ──────────────────────────────────────────
    # Search history
    # ──────────────────────────────────────────

    def save_search_history(self, username: str, query: str, filters: Dict[str, Any],
                            results: List[int]) -> int:
        """Save a search history entry. Returns the entry ID."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO search_history (username, query, filters, results, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    username.lower(),
                    query,
                    json.dumps(filters),
                    json.dumps(results),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_search_history(self, username: str, limit: int = 20,
                           offset: int = 0) -> List[SearchHistoryEntry]:
        """Get search history for a user, most recent first."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT id, username, query, filters, results, created_at
                   FROM search_history
                   WHERE username = ?
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (username.lower(), limit, offset),
            ).fetchall()
            entries = []
            for row in rows:
                entries.append(SearchHistoryEntry(
                    id=row["id"],
                    username=row["username"],
                    query=row["query"],
                    filters=json.loads(row["filters"]),
                    results=json.loads(row["results"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                ))
            return entries
