"""
Taste Profile / Anime DNA Engine.

Takes a user's anime list and computes their taste profile:
- Genre affinities (weighted by score + completion status)
- Tag preferences (weighted similarly, with rank/spoiler awareness)
- Studio loyalty
- Demographic biases
- Rating patterns (average, variance, harsh critic detection)
- Binge potential
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from models import (
    BingePotential,
    DemographicAffinity,
    GenreAffinity,
    RatingPatterns,
    StudioAffinity,
    TagAffinity,
    TasteProfile,
    UserAnime,
    UserAnimeStatus,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Weights & thresholds
# ──────────────────────────────────────────────

# Score weighting: how much a user's rating influences affinity
SCORE_WEIGHT_MULTIPLIER = 0.1  # Each point above 5 adds 10% weight

# Status multipliers for weighting
STATUS_WEIGHTS = {
    UserAnimeStatus.COMPLETED: 1.0,
    UserAnimeStatus.CURRENT: 0.7,
    UserAnimeStatus.REPEATING: 1.2,
    UserAnimeStatus.PAUSED: 0.5,
    UserAnimeStatus.DROPPED: 0.2,
    UserAnimeStatus.PLANNING: 0.1,
}

# How much tag rank affects the weight
TAG_RANK_WEIGHT = 0.01  # Each rank point adds 1% weight

# Harsh critic threshold: if avg score < this, user is a harsh critic
HARSH_CRITIC_THRESHOLD = 5.5

# Number of top items to keep in each category
TOP_N_GENRES = 15
TOP_N_TAGS = 20
TOP_N_STUDIOS = 10
TOP_N_DEMOGRAPHICS = 5


# ──────────────────────────────────────────────
# Profile computation
# ──────────────────────────────────────────────

class TasteProfileEngine:
    """Computes a TasteProfile from a list of UserAnime entries."""

    def __init__(self, username: str, anime_list: List[UserAnime]):
        self.username = username
        self.anime_list = anime_list

    def compute(self) -> TasteProfile:
        """Compute the full taste profile."""
        genre_scores = self._compute_genre_affinities()
        tag_scores = self._compute_tag_affinities()
        studio_scores = self._compute_studio_affinities()
        demo_scores = self._compute_demographic_affinities()
        rating_patterns = self._compute_rating_patterns()
        binge_potential = self._compute_binge_potential()

        return TasteProfile(
            username=self.username,
            totalAnime=len(self.anime_list),
            totalEpisodes=sum(
                ua.anime.episodes or 0 for ua in self.anime_list
                if ua.status == UserAnimeStatus.COMPLETED
            ),
            topGenres=[
                GenreAffinity(genre=g, score=s, count=c)
                for g, s, c in genre_scores[:TOP_N_GENRES]
            ],
            topTags=[
                TagAffinity(tag=t, id=i, score=s, count=c)
                for t, i, s, c in tag_scores[:TOP_N_TAGS]
            ],
            topStudios=[
                StudioAffinity(studio=s, id=i, score=sc, count=c)
                for s, i, sc, c in studio_scores[:TOP_N_STUDIOS]
            ],
            topDemographics=[
                DemographicAffinity(demographic=d, score=s, count=c)
                for d, s, c in demo_scores[:TOP_N_DEMOGRAPHICS]
            ],
            ratingPatterns=rating_patterns,
            bingePotential=binge_potential,
        )

    def _get_weight(self, ua: UserAnime) -> float:
        """Compute the base weight for a user anime entry."""
        status_weight = STATUS_WEIGHTS.get(ua.status, 0.5)
        score = ua.score or 5
        score_weight = 1.0 + (score - 5.0) * SCORE_WEIGHT_MULTIPLIER
        return status_weight * max(score_weight, 0.0)

    def _compute_genre_affinities(self) -> List[Tuple[str, float, int]]:
        """Compute weighted genre affinities, normalized to 0-100 scale."""
        scores: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = Counter()

        for ua in self.anime_list:
            weight = self._get_weight(ua)
            for genre in ua.anime.genres:
                scores[genre] += weight
                counts[genre] += 1

        if not scores:
            return []

        # Normalize to percentage (highest = 100)
        max_score = max(scores.values())
        normalized = {
            g: (s / max_score * 100.0) if max_score > 0 else 0.0
            for g, s in scores.items()
        }

        sorted_genres = sorted(
            normalized.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(g, round(s, 1), counts[g]) for g, s in sorted_genres]

    def _compute_tag_affinities(self) -> List[Tuple[str, int, float, int]]:
        """Compute weighted tag affinities, normalized to 0-100 scale."""
        scores: Dict[int, float] = defaultdict(float)
        names: Dict[int, str] = {}
        counts: Dict[int, int] = Counter()

        for ua in self.anime_list:
            weight = self._get_weight(ua)
            for tag in ua.anime.tags:
                tag_weight = weight * (1.0 + tag.rank * TAG_RANK_WEIGHT)
                scores[tag.id] += tag_weight
                names[tag.id] = tag.name
                counts[tag.id] += 1

        if not scores:
            return []

        # Normalize to percentage (highest = 100)
        max_score = max(scores.values())
        normalized = {
            tid: (s / max_score * 100.0) if max_score > 0 else 0.0
            for tid, s in scores.items()
        }

        sorted_tags = sorted(
            normalized.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            (names[tid], tid, round(score, 1), counts[tid])
            for tid, score in sorted_tags
        ]

    def _compute_studio_affinities(self) -> List[Tuple[str, int, float, int]]:
        """Compute weighted studio affinities."""
        scores: Dict[int, float] = defaultdict(float)
        names: Dict[int, str] = {}
        counts: Dict[int, int] = Counter()

        for ua in self.anime_list:
            weight = self._get_weight(ua)
            for studio in ua.anime.studios:
                scores[studio.id] += weight
                names[studio.id] = studio.name
                counts[studio.id] += 1

        sorted_studios = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            (names[sid], sid, score, counts[sid])
            for sid, score in sorted_studios
        ]

    def _compute_demographic_affinities(self) -> List[Tuple[str, float, int]]:
        """Compute weighted demographic affinities."""
        scores: Dict[str, float] = defaultdict(float)
        counts: Dict[str, int] = Counter()

        for ua in self.anime_list:
            weight = self._get_weight(ua)
            for demo in ua.anime.demographics:
                scores[demo] += weight
                counts[demo] += 1

        sorted_demos = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(d, s, counts[d]) for d, s in sorted_demos]

    def _compute_rating_patterns(self) -> RatingPatterns:
        """Analyze the user's rating patterns."""
        scores = [
            ua.score for ua in self.anime_list
            if ua.score is not None and ua.score > 0
        ]

        if not scores:
            return RatingPatterns()

        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)

        # Scale AniList 0-100 to 1-10 for display
        avg_scaled = avg / 10.0

        # Harsh critic detection
        is_harsh = avg_scaled < HARSH_CRITIC_THRESHOLD
        harsh_critic_score = max(0.0, (HARSH_CRITIC_THRESHOLD - avg_scaled) / HARSH_CRITIC_THRESHOLD)

        # Count generous (>8) and harsh (<4) ratings
        generous = sum(1 for s in scores if s > 80)
        harsh = sum(1 for s in scores if s < 40)

        return RatingPatterns(
            averageScore=round(avg_scaled, 2),
            variance=round(variance / 100.0, 2),
            harshCritic=is_harsh,
            harshCriticScore=round(harsh_critic_score, 2),
            generousCount=generous,
            harshCount=harsh,
        )

    def _compute_binge_potential(self) -> BingePotential:
        """Compute the user's binge-watching potential."""
        completed = [
            ua for ua in self.anime_list
            if ua.status == UserAnimeStatus.COMPLETED
        ]
        total_episodes = sum(ua.anime.episodes or 0 for ua in completed)

        # Average completion % (for shows they started)
        started = [
            ua for ua in self.anime_list
            if ua.status in (
                UserAnimeStatus.COMPLETED,
                UserAnimeStatus.CURRENT,
                UserAnimeStatus.PAUSED,
            )
        ]
        completion_pcts = []
        for ua in started:
            total = ua.anime.episodes or 1
            progress = ua.progress or 0
            pct = min(progress / total, 1.0)
            completion_pcts.append(pct)

        avg_completion = (
            sum(completion_pcts) / len(completion_pcts)
            if completion_pcts else 0.0
        )

        # Binge score: combination of total episodes watched and completion rate
        episode_factor = min(total_episodes / 1000.0, 1.0)  # normalize to 0-1
        completion_factor = avg_completion
        count_factor = min(len(completed) / 100.0, 1.0)

        binge_score = (episode_factor * 0.4 + completion_factor * 0.4 + count_factor * 0.2)

        return BingePotential(
            totalEpisodes=total_episodes,
            completedAnime=len(completed),
            averageCompletionPct=round(avg_completion, 2),
            bingeScore=round(binge_score, 2),
        )
