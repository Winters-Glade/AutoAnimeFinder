---
name: auto-anime-finder
description: "AI-powered anime recommendation engine that connects to AniList (and MyAnimeList) to analyze user taste profiles and deliver personalized recommendations via mood-based or direct-filter modes. Use when the user wants to: (1) get anime recommendations based on their mood or preferences, (2) analyze their anime taste profile (Anime DNA), (3) import and explore their AniList or MAL anime lists, (4) deploy or run the AutoAnimeFinder web application, or (5) understand how anime recommendation algorithms work."
---

# AutoAnimeFinder

AI-powered anime recommendation engine. Connect AniList or MyAnimeList, decode your Anime DNA, and get personalized recommendations via mood-based or direct-filter modes.

## Quick Start

### Run Locally

```bash
# Setup (one time)
cd scripts && bash setup.sh

# Start both backend and frontend
bash scripts/start.sh
```

Then open **http://localhost:5173**, enter your AniList username, and click **Import**.

### Deploy to Render (free)

1. Push `assets/backend/` to a Git repo
2. In Render dashboard → **New Web Service** → point to that repo
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. In Render → **New Static Site** → point `assets/frontend/dist/` to Render Static Sites
   - Set root directory to `assets/frontend/dist`
   - No build command required (already built)

Cost: **$0/mo on free tier** (backend sleeps after 15 min idle, wakes in 5-10s).

## Capabilities

### 1. Import Anime Lists

Connect your **AniList** or **MyAnimeList** (via Jikan API) account by username. Fetches:
- All list statuses: Watching, Completed, On Hold, Dropped, Planning
- Your ratings (1-10 scale for AniList, 1-10 for MAL)
- Full metadata: genres, tags, studios, demographics, synopsis, scores

**Trigger**: The user enters a username and clicks Import.

### 2. Anime DNA / Taste Profile

Analyses the user's list to build a taste profile:

| Metric | Description |
|---|---|
| Genre Affinities | Weighted preference score for each genre |
| Tag Preferences | AniList tag-based preference analysis |
| Studio Loyalty | Which studios the user consistently rates highest |
| Demographic Bias | Shounen, Seinen, Shoujo, Josei preference |
| Critic Type | Harsh (avg < 5) vs Generous (avg >= 5) |
| Binge Potential | Total episodes / completed count, 0-100 |

**Trigger**: After importing a list, the TasteProfile component renders in the sidebar.

### 3. Mood Translator (Signature Feature)

Natural language mood query → anime recommendations. Example inputs:
- "Something dark and psychological after a bad day"
- "I want to feel warm and fuzzy like a hug"
- "Mind-bending sci-fi that makes me think"
- "Lighthearted comedy to forget my problems"

**Keyword mappings** (26+ categories):
| Keyword | Matches Genres/Tags |
|---|---|
| dark, psychological, mind-bending → | thriller, psychological, horror, mystery |
| funny, comedy, hilarious → | comedy, parody, gag |
| sad, emotional, cry → | drama, romance, tragedy |
| action-packed, intense → | action, adventure, shounen |
| relaxing, chill, healing → | slice-of-life, iyashikei, comedy |

**Filters**:
- **Brain Power** (1-100): Low = action/comedy, Medium = drama/scifi, High = psychological/philosophical
- **Time Commitment**: Quick (1-12eps) / Session (13-24) / Commitment (25-100) / Ongoing
- **Mood Intent**: Escape (fantasy/isekai) / Feel Better (comedy/slice-of-life) / Lean In (psychological/drama) / Surprise Me (unique/sci-fi)
- **Avoid List**: Exclude specific genres or tags
- **Dismiss**: Remove specific anime from results

**Trigger**: User types a mood description and clicks "Discover Perfect Match".

### 4. Direct Mode

Alternative to mood — pick genres and filters directly:
- Genre multi-select grid (Action, Comedy, Drama, Fantasy, etc.)
- Same filter controls (time commitment, mood intent, avoid list)
- "Get Recommendations" button

**Trigger**: User switches to Direct Mode tab and selects genres.

### 5. Content-Based Recommendation Algorithm

When enough data exists (user has rated anime), the engine computes **genre/tag vector cosine similarity** between the user's highly-rated shows and all known anime. Returns ranked matches with match scores and reasons.

### 6. Search History

Auto-saves every search (mood query + filters + results). Browseable sidebar to restore previous searches.

## Architecture

```
User → React Frontend (Vite + Tailwind) → FastAPI Backend → AniList GraphQL API
                                                        → Jikan API (MAL backup)
                                                        → SQLite Cache
```

- **Backend**: FastAPI on port 8000, async httpx, SQLite storage
- **Frontend**: React 18 + Vite + Tailwind, dark cyberpunk theme
- **Caching**: SQLite (anime metadata 24h, user lists 1h)
- **Rate Limiting**: AniList 90 req/min, Jikan 1 req/sec

## Resources

### scripts/
- `setup.sh` — Install deps and build frontend (one-time)
- `start.sh` — Launch both backend (:8000) and frontend (:5173)
- `deploy.sh` — Render deployment instructions

### assets/backend/
All Python backend files:
- `models.py` — Pydantic data models
- `anilist_client.py` — AniList GraphQL integration
- `jikan_client.py` — MAL backup via Jikan API
- `taste_profile.py` — Anime DNA analysis engine
- `recommender.py` — Hybrid recommendation engine
- `storage.py` — SQLite cache and history
- `main.py` — FastAPI server with 8 endpoints
- `requirements.txt` — Python dependencies

### assets/frontend/
React + Vite + Tailwind source and production build:
- `src/pages/HomePage.jsx` — Main orchestrating page
- `src/components/` — AnimeCard, TasteProfile, MoodTranslator, DirectMode, FilterControls, NeuralLoader, SearchHistory, Header
- `src/api/client.js` — API client for all endpoints
- `dist/` — Production build (ready to serve)

### references/
- `api-docs.md` — Full API contract with all 8 endpoints, data models, examples
