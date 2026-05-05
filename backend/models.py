"""
Data models for the anime-soul-whisper recommendation engine.

Defines all Pydantic models used across the API, client integrations,
taste profiling, and recommendation engine.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class AnimeStatus(str, Enum):
    """Air/publishing status of an anime."""
    FINISHED = "FINISHED"
    RELEASING = "RELEASING"
    NOT_YET_RELEASED = "NOT_YET_RELEASED"
    CANCELLED = "CANCELLED"
    HIATUS = "HIATUS"


class UserAnimeStatus(str, Enum):
    """User's personal status for an anime in their list."""
    CURRENT = "CURRENT"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    DROPPED = "DROPPED"
    PLANNING = "PLANNING"
    REPEATING = "REPEATING"


class Season(str, Enum):
    """Broadcast season."""
    WINTER = "WINTER"
    SPRING = "SPRING"
    SUMMER = "SUMMER"
    FALL = "FALL"


class Format(str, Enum):
    """Media format."""
    TV = "TV"
    TV_SHORT = "TV_SHORT"
    OVA = "OVA"
    ONA = "ONA"
    MOVIE = "MOVIE"
    SPECIAL = "SPECIAL"
    MUSIC = "MUSIC"


class Source(str, Enum):
    """Source material type."""
    ORIGINAL = "ORIGINAL"
    MANGA = "MANGA"
    LIGHT_NOVEL = "LIGHT_NOVEL"
    VISUAL_NOVEL = "VISUAL_NOVEL"
    VIDEO_GAME = "VIDEO_GAME"
    OTHER = "OTHER"
    NOVEL = "NOVEL"
    DOUJINSHI = "DOUJINSHI"
    ANIME = "ANIME"
    WEB_MANGA = "WEB_MANGA"
    NOVEL_CG = "NOVEL_CG"
    MUSIC = "MUSIC"
    GAME = "GAME"
    BOOK = "BOOK"
    CARTOON = "CARTOON"
    COMIC = "COMIC"
    LIVE_ACTION = "LIVE_ACTION"
    PICTURE_BOOK = "PICTURE_BOOK"
    RADIO = "RADIO"
    TV_GAME = "TV_GAME"


class MoodIntent(str, Enum):
    """High-level mood categories for AI-powered recommendations."""
    ESCAPE = "escape"
    FEEL_BETTER = "feel_better"
    LEAN_IN = "lean_in"
    SURPRISE = "surprise"


class TimeCommitment(str, Enum):
    """Time commitment filter for recommendations."""
    QUICK = "quick"               # 1-12 episodes
    SESSION = "session"           # 13-24 episodes
    COMMITMENT = "commitment"     # 25-100 episodes
    ONGOING = "ongoing"           # Currently airing


# ──────────────────────────────────────────────
# Core data models
# ──────────────────────────────────────────────

class FuzzyDate(BaseModel):
    """Flexible date representation (year/month/day may be null)."""
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None


class AnimeTitle(BaseModel):
    """Anime title in different languages."""
    romaji: Optional[str] = None
    english: Optional[str] = None
    native: Optional[str] = None


class Tag(BaseModel):
    """Anime tag with rank and spoiler info."""
    id: int
    name: str
    rank: int = 0
    isGeneralSpoiler: bool = False
    isMediaSpoiler: bool = False


class NextAiringEpisode(BaseModel):
    """Information about the next scheduled airing."""
    airingAt: Optional[int] = None  # Unix timestamp
    timeUntilAiring: Optional[int] = None
    episode: Optional[int] = None


class Studio(BaseModel):
    """Animation studio."""
    id: int
    name: str
    isAnimationStudio: bool = True


class ExternalLink(BaseModel):
    """External link (streaming, social, info) for an anime."""
    site: str
    url: str
    type: Optional[str] = None  # "STREAMING", "SOCIAL", "INFO"


class StreamingEpisode(BaseModel):
    """A streaming episode with title, URL, and site."""
    title: Optional[str] = None
    url: Optional[str] = None
    site: Optional[str] = None


class AnimeRelation(BaseModel):
    """Related anime entry."""
    id: int
    title: AnimeTitle
    relationType: str  # e.g., "PREQUEL", "SEQUEL", "SIDE_STORY"
    format: Optional[str] = None


class AnimeRecommendation(BaseModel):
    """Recommended anime from AniList's built-in rec system."""
    id: int
    title: AnimeTitle
    rating: Optional[int] = None


class CoverImage(BaseModel):
    """Anime cover image URLs."""
    large: Optional[str] = None
    medium: Optional[str] = None


class Anime(BaseModel):
    """Full anime metadata model."""
    id: int
    idMal: Optional[int] = None
    title: AnimeTitle
    genres: List[str] = Field(default_factory=list)
    tags: List[Tag] = Field(default_factory=list)
    studios: List[Studio] = Field(default_factory=list)
    demographics: List[str] = Field(default_factory=list)
    season: Optional[Season] = None
    seasonYear: Optional[int] = None
    status: Optional[AnimeStatus] = None
    episodes: Optional[int] = None
    duration: Optional[int] = None  # minutes per episode
    format: Optional[Format] = None
    source: Optional[Source] = None
    synonyms: List[str] = Field(default_factory=list)
    meanScore: Optional[int] = None  # 0-100
    averageScore: Optional[int] = None
    popularity: Optional[int] = None
    synopsis: Optional[str] = None  # aka description
    description: Optional[str] = None
    coverImage: Optional[CoverImage] = None
    bannerImage: Optional[str] = None
    startDate: Optional[FuzzyDate] = None
    endDate: Optional[FuzzyDate] = None
    nextAiringEpisode: Optional[NextAiringEpisode] = None
    relations: List[AnimeRelation] = Field(default_factory=list)
    recommendations: List[AnimeRecommendation] = Field(default_factory=list)
    externalLinks: List[ExternalLink] = Field(default_factory=list)
    streamingEpisodes: List[StreamingEpisode] = Field(default_factory=list)


class UserAnime(BaseModel):
    """Anime entry with the user's personal data."""
    anime: Anime
    userId: Optional[int] = None
    score: Optional[int] = None       # 0-100 (AniList raw) → scaled to 1-10
    progress: Optional[int] = None    # episodes watched
    status: Optional[UserAnimeStatus] = None
    startedAt: Optional[FuzzyDate] = None
    completedAt: Optional[FuzzyDate] = None
    repeat: Optional[int] = 0


# ──────────────────────────────────────────────
# Taste Profile models
# ──────────────────────────────────────────────

class GenreAffinity(BaseModel):
    """Genre affinity score."""
    genre: str
    score: float
    count: int

class TagAffinity(BaseModel):
    """Tag affinity score."""
    tag: str
    id: int
    score: float
    count: int

class StudioAffinity(BaseModel):
    """Studio affinity score."""
    studio: str
    id: int
    score: float
    count: int

class DemographicAffinity(BaseModel):
    """Demographic affinity score."""
    demographic: str
    score: float
    count: int

class RatingPatterns(BaseModel):
    """Analysis of the user's rating behavior."""
    averageScore: float = 0.0
    variance: float = 0.0
    harshCritic: bool = False
    harshCriticScore: float = 0.0
    generousCount: int = 0
    harshCount: int = 0

class BingePotential(BaseModel):
    """Measure of the user's binge-watching tendency."""
    totalEpisodes: int = 0
    completedAnime: int = 0
    averageCompletionPct: float = 0.0
    bingeScore: float = 0.0

class TasteProfile(BaseModel):
    """Complete taste profile computed from a user's anime list."""
    username: str
    totalAnime: int = 0
    totalEpisodes: int = 0
    completedAnime: int = 0
    topGenres: List[GenreAffinity] = Field(default_factory=list)
    topTags: List[TagAffinity] = Field(default_factory=list)
    topStudios: List[StudioAffinity] = Field(default_factory=list)
    topDemographics: List[DemographicAffinity] = Field(default_factory=list)
    ratingPatterns: RatingPatterns = Field(default_factory=RatingPatterns)
    bingePotential: BingePotential = Field(default_factory=BingePotential)
    computedAt: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class AnilistFetchRequest(BaseModel):
    """Request body for fetching a user's AniList data."""
    username: str


class JikanFetchRequest(BaseModel):
    """Request body for fetching a user's MAL data via Jikan."""
    username: str


class TasteProfileRequest(BaseModel):
    """Request to get a taste profile."""
    username: str
    source: str = "anilist"  # "anilist" or "mal"


class MoodRecommendationRequest(BaseModel):
    """AI-powered mood-based recommendation request."""
    username: Optional[str] = ""
    moodQuery: str = ""
    brainPower: Optional[int] = Field(default=50, ge=1, le=100)
    timeCommitment: Optional[TimeCommitment] = None
    moodIntent: Optional[MoodIntent] = None
    avoidList: List[str] = Field(default_factory=list)
    excludeList: List[int] = Field(default_factory=list)  # anime IDs to exclude


class DirectRecommendationRequest(BaseModel):
    """Direct filter-based recommendation request (no AI mood)."""
    username: Optional[str] = ""
    genres: List[str] = Field(default_factory=list)
    timeCommitment: Optional[TimeCommitment] = None
    brainPower: Optional[int] = Field(default=50, ge=1, le=100)
    mood: str = ""
    avoidList: List[str] = Field(default_factory=list)
    excludeList: List[int] = Field(default_factory=list)
    limit: int = 20


class RecommendRequest(BaseModel):
    """Simple recommend request body."""
    username: str
    source: str = "anilist"
    limit: int = 20


class Recommendation(BaseModel):
    """Single recommendation result."""
    anime: Anime
    matchReason: str = ""
    matchScore: float = 0.0
    matchedOn: List[str] = Field(default_factory=list)  # which signals triggered


class RecommendationResponse(BaseModel):
    """Full recommendation response."""
    recommendations: List[Recommendation]
    source: str  # "content_based", "ai_mood", "fallback", "direct"
    totalMatches: int = 0


class SearchHistoryEntry(BaseModel):
    """A saved search history entry."""
    id: Optional[int] = None
    username: Optional[str] = ""
    query: str = ""
    filters: dict = Field(default_factory=dict)
    results: List[int] = Field(default_factory=list)  # anime IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchHistoryList(BaseModel):
    """List of search history entries."""
    entries: List[SearchHistoryEntry] = Field(default_factory=list)


class AnimeListResponse(BaseModel):
    """Response for AniList/Jikan fetch endpoints."""
    username: str
    source: str
    animeList: List[UserAnime]
    totalCount: int = 0
    fetchedAt: datetime = Field(default_factory=datetime.utcnow)
