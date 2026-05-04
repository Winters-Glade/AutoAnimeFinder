"""
Hybrid recommendation engine for anime-soul-whisper.

Combines content-based filtering (genre/tag vector similarity),
mood-based query parsing, and direct filter-based recommendations.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

from models import (
    Anime,
    DirectRecommendationRequest,
    MoodIntent,
    MoodRecommendationRequest,
    Recommendation,
    RecommendationResponse,
    TimeCommitment,
    UserAnime,
    UserAnimeStatus,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Scoring weights
# ──────────────────────────────────────────────

GENRE_WEIGHT = 0.6
TAG_WEIGHT = 0.4
SCORE_THRESHOLD = 7  # user score >= this = "liked"

# ──────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def _anime_to_feature_vector(anime: Anime, all_genres: List[str], all_tags: List[str]) -> List[float]:
    """Convert an Anime to a genre/tag feature vector."""
    genre_set = set(g.lower() for g in anime.genres)
    tag_set = set(t.name.lower() for t in anime.tags)

    vec = []
    for genre in all_genres:
        vec.append(1.0 if genre in genre_set else 0.0)
    for tag_name in all_tags:
        vec.append(1.0 if tag_name in tag_set else 0.0)

    return vec


def _build_feature_space(anime_list: List[Anime]) -> Tuple[List[str], List[str]]:
    """Build the full genre and tag vocabularies from a list of anime."""
    all_genres: Set[str] = set()
    all_tags: Set[str] = set()

    for a in anime_list:
        for g in a.genres:
            all_genres.add(g.lower())
        for t in a.tags:
            all_tags.add(t.name.lower())

    return sorted(all_genres), sorted(all_tags)


# ──────────────────────────────────────────────
# Content-based filtering
# ──────────────────────────────────────────────


async def content_based(user_list: List[UserAnime], all_anime: List[Anime]) -> List[Recommendation]:
    """
    Content-based recommendation.

    For each anime the user rated >= 7, find similar anime (from all_anime)
    by genre/tag cosine similarity. Returns ranked deduplicated results.
    """
    liked_ids: Set[int] = set()
    liked_features: List[Tuple[int, List[float]]] = []

    # Build the unified feature space from all_anime
    all_genres, all_tags = _build_feature_space(all_anime)

    for ua in user_list:
        score = ua.score or 0
        if score >= SCORE_THRESHOLD * 10:  # score is 0-100, threshold is 70
            liked_ids.add(ua.anime.id)
            vec = _anime_to_feature_vector(ua.anime, all_genres, all_tags)
            liked_features.append((ua.anime.id, vec))

    if not liked_features:
        logger.info("No liked anime found (score >= %d)", SCORE_THRESHOLD)
        return []

    # Precompute feature vectors for all candidate anime (excluding liked ones)
    candidate_vecs: Dict[int, List[float]] = {}
    for anime in all_anime:
        if anime.id not in liked_ids:
            candidate_vecs[anime.id] = _anime_to_feature_vector(anime, all_genres, all_tags)

    # For each liked anime, find top similar candidates
    similarity_scores: Dict[int, float] = defaultdict(float)
    match_reasons: Dict[int, List[str]] = defaultdict(list)

    for liked_id, liked_vec in liked_features:
        for cand_id, cand_vec in candidate_vecs.items():
            sim = cosine_similarity(liked_vec, cand_vec)
            if sim > 0:
                similarity_scores[cand_id] += sim
                # Track which liked anime contributed
                liked_anime = next((ua.anime for ua in user_list if ua.anime.id == liked_id), None)
                if liked_anime:
                    reason = f"Similar to {liked_anime.title.romaji or liked_anime.title.english or 'anime #' + str(liked_id)}"
                    if reason not in match_reasons[cand_id]:
                        match_reasons[cand_id].append(reason)

    # Rank by total similarity score
    ranked = sorted(similarity_scores.items(), key=lambda x: x[1], reverse=True)

    # Build Recommendation objects
    anime_by_id = {a.id: a for a in all_anime}
    recommendations = []
    for cand_id, total_sim in ranked:
        anime = anime_by_id.get(cand_id)
        if not anime:
            continue
        reasons = match_reasons.get(cand_id, [])
        matched_on = []
        if reasons:
            matched_on = ["content_based"]

        recommendations.append(
            Recommendation(
                anime=anime,
                matchScore=round(total_sim, 4),
                matchReason="; ".join(reasons[:3]),
                matchedOn=matched_on,
            )
        )

    return recommendations


# ──────────────────────────────────────────────
# Mood-based recommendations
# ──────────────────────────────────────────────

# Mapping from mood intent keywords to genres/tags
MOOD_INTENT_MAP = {
    MoodIntent.ESCAPE: {
        "genres": ["fantasy", "isekai", "action", "adventure", "sci-fi"],
        "tags": ["fantasy", "isekai", "magic", "adventure", "swords", "parallel universe"],
    },
    MoodIntent.FEEL_BETTER: {
        "genres": ["comedy", "slice of life", "romance"],
        "tags": ["comedy", "slice of life", "romance", "heartwarming", "feel good", "cute"],
    },
    MoodIntent.LEAN_IN: {
        "genres": ["psychological", "drama", "thriller", "mystery", "seinen"],
        "tags": ["psychological", "drama", "thriller", "mystery", "philosophical", "dark"],
    },
    MoodIntent.SURPRISE: {
        "genres": ["sci-fi", "fantasy", "psychological"],
        "tags": ["unique", "unexpected", "mind bending", "time travel", "surreal", "abstract"],
    },
}

# Brain power mapping: certain genres/tags indicate high/low cognitive load
HIGH_BRAIN_GENRES = {"psychological", "mystery", "thriller", "seinen"}
HIGH_BRAIN_TAGS = {"psychological", "philosophical", "mind bending", "time travel", "conspiracy", "strategy"}
LOW_BRAIN_GENRES = {"comedy", "action", "slice of life", "ecchi", "romance"}
LOW_BRAIN_TAGS = {"comedy", "slice of life", "cute", "harem", "school", "gag"}


def _parse_mood_query(mood_query: str) -> Dict[str, float]:
    """
    Parse a free-text mood query into keyword weights.

    Returns a dict of lowercase keyword -> weight.
    """
    if not mood_query:
        return {}

    # Normalize
    text = mood_query.lower().strip()

    # Extract keywords (remove common stopwords)
    stopwords = {
        "a", "an", "the", "i", "me", "my", "want", "to", "for", "and", "or",
        "in", "of", "on", "at", "is", "am", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did",
        "but", "if", "so", "like", "some", "something", "that", "this",
        "it", "with", "feeling", "feel", "looking", "watch", "anime",
    }

    # Split by common delimiters
    words = re.split(r"[\s,.;!?]+", text)
    keywords: Dict[str, float] = defaultdict(float)

    # Single words
    for w in words:
        w = w.strip().lower()
        if w and w not in stopwords and len(w) > 1:
            keywords[w] += 1.0

    # Bigrams
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}".strip().lower()
        if bigram and all(w not in stopwords for w in bigram.split()):
            # Check if it's a known multi-word tag/genre
            keywords[bigram] += 2.0

    # Normalize weights
    if keywords:
        max_w = max(keywords.values())
        for k in keywords:
            keywords[k] /= max_w

    return dict(keywords)


def _map_keywords_to_genres_tags(keywords: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Map mood keywords to known genres and tags.
    Returns (genre_weights, tag_weights) dicts.
    """
    # Known genres and tags we can match against
    known_genres = {
        "action", "adventure", "comedy", "drama", "fantasy", "sci-fi", "sci fi",
        "romance", "slice of life", "slice-of-life", "horror", "mystery",
        "thriller", "psychological", "isekai", "mecha", "music", "sports",
        "supernatural", "ecchi", "harem", "shounen", "shoujo", "seinen", "josei",
        "kids", "magic", "military", "parody", "samurai", "space", "vampire",
        "demons", "angels", "game", "school", "suspense",
    }

    known_tags = {
        "comedy", "slice of life", "drama", "fantasy", "romance", "action",
        "psychological", "philosophical", "dark", "heartwarming", "feel good",
        "cute", "thriller", "mystery", "mind bending", "time travel",
        "adventure", "magic", "supernatural", "school", "mecha", "sports",
        "music", "historical", "military", "space", "seinen",
    }

    genre_weights: Dict[str, float] = defaultdict(float)
    tag_weights: Dict[str, float] = defaultdict(float)

    for kw, weight in keywords.items():
        # Direct match
        if kw in known_genres:
            genre_weights[kw] += weight
        if kw in known_tags:
            tag_weights[kw] += weight

        # Fuzzy match: partial overlap
        for known in known_genres:
            if kw in known or known in kw:
                genre_weights[known] += weight * 0.5
        for known in known_tags:
            if kw in known or known in kw:
                tag_weights[known] += weight * 0.5

    return dict(genre_weights), dict(tag_weights)


def _apply_brain_power_filter(
    anime_list: List[Anime],
    brain_power: int,
) -> List[Anime]:
    """Filter or rank by brain power / complexity level (1-100)."""
    if brain_power is None:
        return anime_list

    scored: List[Tuple[Anime, float]] = []
    for a in anime_list:
        complexity = 50  # default mid-range
        genre_lower = [g.lower() for g in a.genres]
        tag_lower = [t.name.lower() for t in a.tags]

        # Boost for high-brain signals
        if any(g in HIGH_BRAIN_GENRES for g in genre_lower):
            complexity += 20
        if any(t in HIGH_BRAIN_TAGS for t in tag_lower):
            complexity += 15

        # Reduce for low-brain signals
        if any(g in LOW_BRAIN_GENRES for g in genre_lower):
            complexity -= 15
        if any(t in LOW_BRAIN_TAGS for t in tag_lower):
            complexity -= 10

        complexity = max(1, min(100, complexity))

        # How close to desired brain_power
        affinity = 1.0 - abs(complexity - brain_power) / 100.0
        scored.append((a, affinity))

    # Sort by affinity descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return [a for a, _ in scored]


def _apply_time_commitment_filter(
    anime_list: List[Anime],
    time_commitment: Optional[TimeCommitment],
) -> List[Anime]:
    """Filter anime by episode count / time commitment."""
    if time_commitment is None:
        return anime_list

    ranges = {
        TimeCommitment.QUICK: (1, 12),
        TimeCommitment.SESSION: (13, 24),
        TimeCommitment.COMMITMENT: (25, 100),
        TimeCommitment.ONGOING: (None, None),  # airing
    }

    ep_min, ep_max = ranges[time_commitment]

    if time_commitment == TimeCommitment.ONGOING:
        return [a for a in anime_list if a.status and a.status.value == "RELEASING"]

    filtered = []
    for a in anime_list:
        eps = a.episodes
        if eps is None:
            continue
        if ep_min is not None and eps < ep_min:
            continue
        if ep_max is not None and eps > ep_max:
            continue
        filtered.append(a)

    return filtered


def _apply_avoid_list(
    anime_list: List[Anime],
    avoid_list: List[str],
) -> List[Anime]:
    """Exclude anime containing any avoided genres or tags."""
    if not avoid_list:
        return anime_list

    avoid_lower = [a.lower().strip() for a in avoid_list]

    filtered = []
    for a in anime_list:
        genres_lower = [g.lower() for g in a.genres]
        tags_lower = [t.name.lower() for t in a.tags]
        all_features = set(genres_lower + tags_lower)

        if not any(av in all_features for av in avoid_lower):
            filtered.append(a)

    return filtered


def _score_mood_match(
    anime: Anime,
    genre_weights: Dict[str, float],
    tag_weights: Dict[str, float],
) -> float:
    """Score how well an anime matches a mood query by genre/tag overlap."""
    score = 0.0

    anime_genres = set(g.lower() for g in anime.genres)
    anime_tags = set(t.name.lower() for t in anime.tags)

    for genre, weight in genre_weights.items():
        if genre in anime_genres:
            score += weight * GENRE_WEIGHT

    for tag_name, weight in tag_weights.items():
        if tag_name in anime_tags:
            score += weight * TAG_WEIGHT

    return score


def _get_mood_intent_signals(mood_intent: Optional[MoodIntent]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Get genre/tag weights from a mood intent."""
    if not mood_intent:
        return {}, {}

    signals = MOOD_INTENT_MAP.get(mood_intent, {})
    genres = {g: 0.8 for g in signals.get("genres", [])}
    tags = {t: 0.7 for t in signals.get("tags", [])}

    return genres, tags


async def mood_based(
    mood_query: str,
    filters: dict,
    all_anime: List[Anime],
) -> List[Recommendation]:
    """
    Mood-based recommendation.

    1. Parse mood_query into keywords
    2. Map keywords to genre/tag weights
    3. Apply filters (brainPower, timeCommitment, moodIntent, avoidList)
    4. Score and rank
    """
    brain_power = filters.get("brainPower", 50)
    time_commitment = filters.get("timeCommitment")
    mood_intent = filters.get("moodIntent")
    avoid_list = filters.get("avoidList", [])
    exclude_list = filters.get("excludeList", [])

    # Parse mood query
    keywords = _parse_mood_query(mood_query)
    genre_weights, tag_weights = _map_keywords_to_genres_tags(keywords)

    # Add mood intent signals
    intent_genres, intent_tags = _get_mood_intent_signals(mood_intent)
    for g, w in intent_genres.items():
        genre_weights[g] = genre_weights.get(g, 0) + w
    for t, w in intent_tags.items():
        tag_weights[t] = tag_weights.get(t, 0) + w

    # Apply filters
    candidates = list(all_anime)
    candidates = _apply_avoid_list(candidates, avoid_list)

    if exclude_list:
        exclude_set = set(exclude_list)
        candidates = [a for a in candidates if a.id not in exclude_set]

    candidates = _apply_time_commitment_filter(candidates, time_commitment)

    # Score each candidate
    scored: List[Tuple[Anime, float, List[str]]] = []
    for a in candidates:
        match_score = _score_mood_match(a, genre_weights, tag_weights)

        # Build matched-on signals
        matched_on = []
        anime_genres = set(g.lower() for g in a.genres)
        anime_tags = set(t.name.lower() for t in a.tags)
        for g in genre_weights:
            if g in anime_genres:
                matched_on.append(f"genre:{g}")
        for t in tag_weights:
            if t in anime_tags:
                matched_on.append(f"tag:{t}")
        if matched_on:
            match_score += 0.01  # ensure non-zero for ranking
            scored.append((a, match_score, matched_on))

    # Apply brain power re-ranking
    if brain_power is not None:
        # For mood + brain, we re-rank the top scored candidates
        scored.sort(key=lambda x: x[1], reverse=True)
        top_scored = scored[:100] if len(scored) > 100 else scored
        rest = scored[100:] if len(scored) > 100 else []
        brain_ranked = _apply_brain_power_filter([a for a, _, _ in top_scored], brain_power)
        brain_order = {a.id: i for i, a in enumerate(brain_ranked)}
        scored = sorted(top_scored, key=lambda x: brain_order.get(x[0].id, 999))
        scored = [(a, s, m) for a, s, m in scored] + rest
    else:
        scored.sort(key=lambda x: x[1], reverse=True)

    # Build recommendations
    recommendations = []
    for anime, score, matched_on in scored:
        # Build a human-readable reason
        reason_parts = []
        for signal in matched_on[:5]:
            if signal.startswith("genre:"):
                reason_parts.append(f"matches genre '{signal[6:]}'")
            elif signal.startswith("tag:"):
                reason_parts.append(f"matches tag '{signal[4:]}'")

        recommendations.append(
            Recommendation(
                anime=anime,
                matchScore=round(score, 4),
                matchReason="; ".join(reason_parts) if reason_parts else "Mood match",
                matchedOn=matched_on,
            )
        )

    return recommendations


# ──────────────────────────────────────────────
# Direct filter-based recommendations
# ──────────────────────────────────────────────


async def direct_filters(
    filters: dict,
    all_anime: List[Anime],
) -> List[Recommendation]:
    """
    Direct filter-based recommendation.
    Apply genre inclusion, time commitment, brain power, and mood filters.
    """
    genres = [g.lower() for g in filters.get("genres", [])]
    time_commitment = filters.get("timeCommitment")
    brain_power = filters.get("brainPower")
    mood = filters.get("mood", "").lower()
    avoid_list = filters.get("avoidList", [])
    exclude_list = filters.get("excludeList", [])
    limit = filters.get("limit", 20)

    candidates = list(all_anime)

    # Exclude list
    if exclude_list:
        exclude_set = set(exclude_list)
        candidates = [a for a in candidates if a.id not in exclude_set]

    # Avoid list
    candidates = _apply_avoid_list(candidates, avoid_list)

    # Genre filter (inclusive OR)
    if genres:
        filtered = []
        for a in candidates:
            anime_genres = [g.lower() for g in a.genres]
            if any(g in anime_genres for g in genres):
                filtered.append(a)
        candidates = filtered

    # Time commitment
    candidates = _apply_time_commitment_filter(candidates, time_commitment)

    # Score by how many selected genres match (for ranking)
    scored: List[Tuple[Anime, float, List[str]]] = []
    for a in candidates:
        matched_on = []
        anime_genres = set(g.lower() for g in a.genres)
        anime_tags = set(t.name.lower() for t in a.tags)

        score = 0.0
        if genres:
            match_count = sum(1 for g in genres if g in anime_genres)
            score += match_count / max(len(genres), 1) * 10
            for g in genres:
                if g in anime_genres:
                    matched_on.append(f"genre:{g}")

        # Boost by popularity as tiebreaker
        if a.popularity:
            score += math.log(a.popularity + 1) * 0.1
        if a.meanScore:
            score += (a.meanScore / 100.0) * 2

        scored.append((a, score, matched_on))

    # Brain power re-ranking
    if brain_power is not None:
        brain_ranked = _apply_brain_power_filter([a for a, _, _ in scored], brain_power)
        brain_order = {a.id: i for i, a in enumerate(brain_ranked)}
        scored.sort(key=lambda x: brain_order.get(x[0].id, 999))
    else:
        scored.sort(key=lambda x: x[1], reverse=True)

    # Limit
    scored = scored[:limit]

    # Build recommendations
    recommendations = []
    for anime, score, matched_on in scored:
        reason_parts = []
        for signal in matched_on:
            if signal.startswith("genre:"):
                reason_parts.append(f"genre '{signal[6:]}'")

        recommendations.append(
            Recommendation(
                anime=anime,
                matchScore=round(score, 4),
                matchReason="Matches: " + ", ".join(reason_parts) if reason_parts else "Direct filter match",
                matchedOn=matched_on,
            )
        )

    return recommendations


# ──────────────────────────────────────────────
# Auto-recommendations (zero-input)
# ──────────────────────────────────────────────


async def auto_recommend(
    user_anime_list: List[UserAnime],
    all_anime: List[Anime],
    seed_count: int = 5,
    limit: int = 20,
) -> List[Recommendation]:
    """
    Zero-input auto recommendations based on the user's recently completed
    high-rated anime.

    1. Finds recently completed anime with score > 70
    2. Falls back to any high-rated anime if no completed entries
    3. Builds weighted genre/tag profile from seed anime
    4. Scores all unseen anime by profile match
    5. Returns top N recommendations
    """
    # 1. Filter: COMPLETED + score > 70 (0-100 scale used by AniList/Jikan clients)
    completed_high_rated = [
        ua
        for ua in user_anime_list
        if ua.status == UserAnimeStatus.COMPLETED and (ua.score or 0) > 70
    ]

    # Sort by completedAt descending (most recently completed first)
    def _sort_key(ua: UserAnime) -> tuple:
        if ua.completedAt is None:
            return (0, 0, 0)
        return (
            ua.completedAt.year or 0,
            ua.completedAt.month or 0,
            ua.completedAt.day or 0,
        )

    completed_high_rated.sort(key=_sort_key, reverse=True)
    seed_anime = completed_high_rated[:seed_count]

    # Fallback: use any high-rated anime if no completed entries
    if not seed_anime:
        high_rated = [ua for ua in user_anime_list if (ua.score or 0) > 70]
        high_rated.sort(key=lambda ua: ua.completedAt is not None, reverse=True)
        seed_anime = high_rated[:seed_count]

    if not seed_anime:
        logger.info("No high-rated anime found for auto-recommend")
        return []

    # 2. Build genre/tag weights from seed anime
    genre_counts: Dict[str, int] = defaultdict(int)
    tag_counts: Dict[str, int] = defaultdict(int)

    for ua in seed_anime:
        for genre in ua.anime.genres or []:
            genre_counts[genre] += 1
        for tag in ua.anime.tags or []:
            tag_counts[tag.name] += 1

    # Normalize weights to 0.0-1.0
    max_genre_count = max(genre_counts.values()) if genre_counts else 1
    max_tag_count = max(tag_counts.values()) if tag_counts else 1
    genre_weights = {g: c / max_genre_count for g, c in genre_counts.items()}
    tag_weights = {t: c / max_tag_count for t, c in tag_counts.items()}

    # 3. Determine watched anime IDs to exclude
    watched_ids = {ua.anime.id for ua in user_anime_list}

    # 4. Score all unseen anime by weighted profile match
    scored: List[Tuple[float, Anime]] = []
    for anime in all_anime:
        if anime.id in watched_ids:
            continue

        score = 0.0
        total_weight = 0.0

        # Genre matching
        for genre in anime.genres or []:
            w = genre_weights.get(genre, 0)
            score += w
            total_weight += 1.0

        # Tag matching (weighted half as much as genres)
        for tag in anime.tags or []:
            w = tag_weights.get(tag.name, 0)
            score += w * 0.5
            total_weight += 0.5

        if total_weight > 0:
            normalized_score = score / total_weight
            scored.append((normalized_score, anime))

    # 5. Sort by score descending, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    top_scored = scored[:limit]

    # Build Recommendation objects
    recommendations = []
    for norm_score, anime in top_scored:
        recommendations.append(
            Recommendation(
                anime=anime,
                matchScore=round(norm_score, 4),
                matchReason="Auto: Based on your recent favorites",
                matchedOn=["auto_recommend"],
            )
        )

    return recommendations


# ──────────────────────────────────────────────
# Auto recommendations (zero-input)
# ──────────────────────────────────────────────


async def auto_recommend(
    user_anime_list: List[UserAnime],
    all_anime: List[Anime],
    seed_count: int = 5,
) -> List[Recommendation]:
    """
    Zero-input auto recommendations based on the user's recently completed
    high-rated anime.

    Algorithm:
      1. Find completed anime with score > 70
      2. Sort by completedAt descending, take up to *seed_count*
      3. Build weighted genre/tag profile from seed anime
      4. Score all unseen anime against the weighted profile
      5. Return top 20 Recommendations

    Falls back to any high-rated anime (regardless of status) if no completed
    entries are found.
    """
    # ── 1. Find completed high-rated anime ──────────────────────────────
    completed_high_rated = [
        ua
        for ua in user_anime_list
        if ua.status == UserAnimeStatus.COMPLETED and (ua.score or 0) > 70
    ]

    # Sort by completedAt descending (most recently completed first)
    def _completed_sort_key(ua: UserAnime) -> tuple:
        if ua.completedAt is None:
            return (0, 0, 0)
        return (
            ua.completedAt.year or 0,
            ua.completedAt.month or 0,
            ua.completedAt.day or 0,
        )

    completed_high_rated.sort(key=_completed_sort_key, reverse=True)
    seeds = completed_high_rated[:seed_count]

    # ── Fallback: any high-rated anime if none completed ────────────────
    if not seeds:
        fallback = [
            ua
            for ua in user_anime_list
            if ua.status != UserAnimeStatus.PLANNING and (ua.score or 0) > 70
        ]
        fallback.sort(key=_completed_sort_key, reverse=True)
        seeds = fallback[:seed_count]

    if not seeds:
        logger.info("No high-rated anime found for auto-recommend")
        return []

    # ── 2. Build weighted genre/tag profile from seeds ──────────────────
    genre_counts: Dict[str, int] = defaultdict(int)
    tag_counts: Dict[str, int] = defaultdict(int)

    for ua in seeds:
        for g in ua.anime.genres:
            genre_counts[g.lower()] += 1
        for t in ua.anime.tags:
            tag_counts[t.name.lower()] += 1

    # Normalise to 0.0-1.0 weights
    max_genre_count = max(genre_counts.values()) if genre_counts else 1
    max_tag_count = max(tag_counts.values()) if tag_counts else 1
    genre_weights = {g: c / max_genre_count for g, c in genre_counts.items()}
    tag_weights = {t: c / max_tag_count for t, c in tag_counts.items()}

    # ── 3. Determine anime to exclude (watched + seeds) ─────────────────
    watched_ids = {
        ua.anime.id
        for ua in user_anime_list
        if ua.status and ua.status != UserAnimeStatus.PLANNING
    }
    seed_ids = {ua.anime.id for ua in seeds}
    exclude_ids = watched_ids | seed_ids

    # ── 4. Score all unseen anime against the weighted profile ──────────
    scored_candidates: List[Tuple[float, Anime, List[str]]] = []

    for anime in all_anime:
        if anime.id in exclude_ids:
            continue

        anime_genres = set(g.lower() for g in anime.genres)
        anime_tags = set(t.name.lower() for t in anime.tags)

        score = 0.0
        matched_signals: List[str] = []
        total_weight = 0.0

        for genre, weight in genre_weights.items():
            if genre in anime_genres:
                score += weight * GENRE_WEIGHT
                matched_signals.append(f"seed_genre:{genre}")
            total_weight += GENRE_WEIGHT

        for tag_name, weight in tag_weights.items():
            if tag_name in anime_tags:
                score += weight * TAG_WEIGHT
                matched_signals.append(f"seed_tag:{tag_name}")
            total_weight += TAG_WEIGHT

        # Normalise score by available weights so anime with many genres/tags
        # aren't unfairly favoured over anime with few.
        if total_weight > 0 and score > 0:
            normalised = score / total_weight
            scored_candidates.append((normalised, anime, matched_signals))

    if not scored_candidates:
        logger.info("No candidates matched the seed profile")
        return []

    # ── 5. Sort, take top 20, wrap in Recommendation objects ────────────
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = scored_candidates[:20]

    seed_titles = [
        s.anime.title.romaji or s.anime.title.english or f"#{s.anime.id}"
        for s in seeds
    ]
    reason_prefix = f"Auto: Based on your recent favourites ({', '.join(seed_titles[:3])})"

    recommendations = []
    for norm_score, anime, _ in top_candidates:
        recommendations.append(
            Recommendation(
                anime=anime,
                matchScore=round(norm_score, 4),
                matchReason=reason_prefix,
                matchedOn=["auto_recommend"],
            )
        )

    return recommendations
