# AutoAnimeFinder — API Contract

> **Project**: AI-powered anime recommendation engine
> **Base URL**: `http://localhost:8000`
> **Protocol**: HTTP/REST + JSON

---

## Table of Contents

1. [Data Models](#1-data-models)
2. [Endpoints](#2-endpoints)
3. [Error Handling](#3-error-handling)
4. [Rate Limiting](#4-rate-limiting)
5. [Caching Strategy](#5-caching-strategy)

---

## 1. Data Models

### 1.1 Anime

```json
{
  "id": 1535,
  "title": {
    "romaji": "Death Note",
    "english": "Death Note",
    "native": "デスノート"
  },
  "genres": ["Mystery", "Psychological", "Supernatural", "Thriller"],
  "tags": [
    { "id": 123, "name": "Psychological", "rank": 85, "isGeneralSpoiler": false, "isMediaSpoiler": false }
  ],
  "studios": [
    { "id": 7, "name": "Madhouse", "isAnimationStudio": true }
  ],
  "demographics": ["Shounen"],
  "season": "FALL",
  "seasonYear": 2006,
  "status": "FINISHED",
  "episodes": 37,
  "duration": 23,
  "format": "TV",
  "source": "MANGA",
  "synonyms": [],
  "meanScore": 86,
  "averageScore": 85,
  "popularity": 350000,
  "synopsis": "A high school student discovers a supernatural notebook...",
  "description": "A high school student discovers a supernatural notebook...",
  "coverImage": { "large": "https://...", "medium": "https://..." },
  "bannerImage": "https://...",
  "startDate": { "year": 2006, "month": 10, "day": 4 },
  "endDate": { "year": 2007, "month": 6, "day": 27 },
  "nextAiringEpisode": null,
  "relations": [
    { "id": 2994, "title": { "romaji": "Death Note: Another Note", "english": null }, "relationType": "SIDE_STORY", "format": "SPECIAL" }
  ],
  "recommendations": [
    { "id": 23273, "title": { "romaji": "Code Geass", "english": "Code Geass" }, "rating": 90 }
  ]
}
```

### 1.2 UserAnime

```json
{
  "anime": { /* Anime object */ },
  "userId": 12345,
  "score": 85,
  "progress": 37,
  "status": "COMPLETED",
  "startedAt": { "year": 2020, "month": 1, "day": 15 },
  "completedAt": { "year": 2020, "month": 2, "day": 1 },
  "repeat": 0
}
```

**Status values**: `CURRENT`, `COMPLETED`, `PAUSED`, `DROPPED`, `PLANNING`, `REPEATING`

### 1.3 TasteProfile

```json
{
  "username": "animefan42",
  "totalAnime": 150,
  "totalEpisodes": 3200,
  "topGenres": [
    { "genre": "Action", "score": 0.92, "count": 45 },
    { "genre": "Psychological", "score": 0.85, "count": 28 }
  ],
  "topTags": [
    { "tag": "Anti-Hero", "id": 234, "score": 0.88, "count": 15 }
  ],
  "topStudios": [
    { "studio": "Madhouse", "id": 7, "score": 0.78, "count": 12 }
  ],
  "topDemographics": [
    { "demographic": "Seinen", "score": 0.74, "count": 35 }
  ],
  "ratingPatterns": {
    "averageScore": 7.2,
    "variance": 2.1,
    "harshCritic": false,
    "harshCriticScore": 0.31,
    "generousCount": 20,
    "harshCount": 8
  },
  "bingePotential": {
    "totalEpisodes": 3200,
    "completedAnime": 120,
    "averageCompletionPct": 0.95,
    "bingeScore": 0.82
  },
  "computedAt": "2026-05-04T10:00:00Z"
}
```

### 1.4 Recommendation

```json
{
  "anime": { /* Anime object */ },
  "matchReason": "Strong genre overlap with your highly-rated shows (Psychological, Thriller)",
  "matchScore": 0.91,
  "matchedOn": ["genres:psychological", "genres:thriller", "tags:anti-hero"]
}
```

### 1.5 SearchHistoryEntry

```json
{
  "id": 1,
  "username": "animefan42",
  "query": "dark psychological thriller",
  "filters": { "brainPower": 70, "timeCommitment": "session" },
  "results": [1535, 23273, 30230],
  "created_at": "2026-05-04T10:30:00Z"
}
```

---

## 2. Endpoints

### 2.1 Fetch Anime List — AniList

> `POST /api/anilist/fetch`

**Description**: Fetches a user's full anime list from AniList, including all statuses with scores. Also fetches full metadata for each anime.

**Request Body**:
```json
{
  "username": "animefan42"
}
```

**Success Response** (200):
```json
{
  "username": "animefan42",
  "source": "anilist",
  "animeList": [ /* UserAnime[] */ ],
  "totalCount": 356,
  "fetchedAt": "2026-05-04T10:00:00Z"
}
```

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Missing username |
| 404 | User not found on AniList |
| 502 | AniList API error / GraphQL failure |
| 429 | Rate limited (90 req/min exceeded) |

---

### 2.2 Fetch Anime List — Jikan (MAL Backup)

> `POST /api/jikan/fetch`

**Description**: Fetches a user's anime list from MyAnimeList using the Jikan API (v4). Used as a backup when AniList is unavailable.

**Request Body**:
```json
{
  "username": "mal_animefan"
}
```

**Success Response** (200):
```json
{
  "username": "mal_animefan",
  "source": "mal",
  "animeList": [ /* UserAnime[] */ ],
  "totalCount": 200,
  "fetchedAt": "2026-05-04T10:00:00Z"
}
```

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Missing username |
| 404 | User not found on MAL |
| 502 | Jikan API error |
| 429 | Rate limited (Jikan rate = 30 req/min, 3 req/sec) |

---

### 2.3 Get Taste Profile

> `GET /api/profile/taste`

**Description**: Computes and returns the user's taste profile from their anime list. The profile is cached per user for 1 hour.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `username` | string | — | AniList/MAL username |
| `source` | string | `"anilist"` | `"anilist"` or `"mal"` |

**Success Response** (200): `TasteProfile` object (see §1.3)

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Missing or empty username |
| 404 | User not found |
| 500 | Taste profile computation failed |

---

### 2.4 Mood-Based Recommendations (AI-Powered)

> `POST /api/recommendations/mood`

**Description**: Takes a natural-language mood query and optional filters, then returns personalized recommendations using the hybrid engine.

**Request Body**:
```json
{
  "username": "animefan42",
  "moodQuery": "something dark and psychological after a bad day",
  "brainPower": 70,
  "timeCommitment": "session",
  "moodIntent": "lean_in",
  "avoidList": ["Ecchi", "Harem"],
  "excludeList": [1535, 23273]
}
```

**Success Response** (200):
```json
{
  "recommendations": [ /* Recommendation[] */ ],
  "source": "ai_mood",
  "totalMatches": 10
}
```

**Source values**: `"content_based"` | `"ai_mood"` | `"fallback"` | `"direct"`

**Brain Power mapping**:
| Range | Label |
|-------|-------|
| 1–25 | Light / mindless fun |
| 26–50 | Moderate |
| 51–75 | Complex |
| 76–100 | Heavy / cerebral |

**Time Commitment mapping**:
| Value | Episodes |
|-------|----------|
| `quick` | 1–12 episodes |
| `session` | 13–24 episodes |
| `commitment` | 25–100 episodes |
| `ongoing` | Currently airing |

**Mood Intent mapping**:
| Value | Themes |
|-------|--------|
| `escape` | Fantasy, Isekai, Adventure |
| `feel_better` | Comedy, Slice-of-Life, Romance |
| `lean_in` | Psychological, Drama, Thriller |
| `surprise` | Unique, Unconventional, Underrated |

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Invalid filter parameters |
| 404 | User not found |
| 500 | Recommendation engine error |

---

### 2.5 Direct Recommendations (Filter-Based)

> `POST /api/recommendations/direct`

**Description**: Returns recommendations based on explicit genre/filter criteria without AI mood analysis.

**Request Body**:
```json
{
  "genres": ["Action", "Psychological"],
  "timeCommitment": "session",
  "brainPower": 60,
  "mood": "",
  "avoidList": ["Ecchi"],
  "excludeList": [],
  "limit": 20
}
```

**Success Response** (200):
```json
{
  "recommendations": [ /* Recommendation[] */ ],
  "source": "direct",
  "totalMatches": 15
}
```

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Invalid parameters |
| 500 | Recommendation engine error |

---

### 2.6 Get Anime Details

> `GET /api/anime/{id}`

**Description**: Returns full metadata for a single anime by its AniList ID.

**Path Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | AniList ID of the anime |

**Success Response** (200): `Anime` object (see §1.1)

**Error Responses**:
| Code | Description |
|------|-------------|
| 404 | Anime not found |
| 502 | AniList API error |

---

### 2.7 Save Search History

> `POST /api/search/save`

**Description**: Saves a search query and its results to the user's search history.

**Request Body**:
```json
{
  "username": "animefan42",
  "query": "dark psychological thriller",
  "filters": { "brainPower": 70, "timeCommitment": "session" },
  "results": [1535, 23273, 30230]
}
```

**Success Response** (201):
```json
{
  "id": 1,
  "message": "Search saved"
}
```

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Invalid request body |

---

### 2.8 List Search History

> `GET /api/search/history?username=animefan42`

**Description**: Returns the user's saved search history, most recent first.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `username` | string | — | Username to fetch history for |
| `limit` | int | 20 | Max entries to return |
| `offset` | int | 0 | Pagination offset |

**Success Response** (200):
```json
{
  "entries": [ /* SearchHistoryEntry[] */ ]
}
```

**Error Responses**:
| Code | Description |
|------|-------------|
| 400 | Missing username |

---

## 3. Error Handling

All errors return a consistent JSON structure:

```json
{
  "detail": {
    "code": "USER_NOT_FOUND",
    "message": "User 'nonexistent' was not found on AniList",
    "source": "anilist_client"
  }
}
```

Status codes:
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (missing/ invalid parameters) |
| 404 | Resource not found |
| 429 | Rate limited |
| 500 | Internal server error |
| 502 | Upstream API error |

---

## 4. Rate Limiting

| Service | Limit | Strategy |
|---------|-------|----------|
| AniList GraphQL | 90 requests/minute | Exponential backoff + queue |
| Jikan (MAL) v4 | 30 req/min / 3 req/sec | Exponential backoff + queue |
| Our API | 60 requests/minute (configurable) | Token bucket per IP |

---

## 5. Caching Strategy

| Data | Cache Duration | Storage |
|------|----------------|---------|
| Anime metadata (by ID) | 24 hours | SQLite / JSON file |
| User anime list | 1 hour | SQLite / JSON file |
| Taste profiles | 1 hour | SQLite / JSON file |
| Search history | Permanent | SQLite / JSON file |
| Recommendation results | 30 minutes (session) | In-memory (ephemeral) |

---

*Last updated: 2026-05-04*
