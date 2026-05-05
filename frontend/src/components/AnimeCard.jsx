import { useState } from 'react'

const PLACEHOLDER = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450" viewBox="0 0 300 450">
    <rect width="300" height="450" fill="#14141f"/>
    <text x="150" y="225" font-family="monospace" font-size="14" fill="#6b7280" text-anchor="middle" dominant-baseline="middle">No Image</text>
  </svg>`
)

function formatScore(s) {
  if (s == null) return null
  const n = typeof s === 'number' ? s : parseFloat(s)
  // AniList meanScore is 0-100, convert to 1-10 scale
  return n > 20 ? (n / 10).toFixed(1) : n.toFixed(1)
}

function scoreColor(s) {
  const n = parseFloat(s)
  if (n >= 8) return 'text-green-400'
  if (n >= 6) return 'text-cyan-400'
  if (n >= 4) return 'text-purple-400'
  return 'text-pink-400'
}

/**
 * Extract a string from a nested title object, or a direct string.
 */
function getTitle(title) {
  if (!title) return null
  if (typeof title === 'string') return title
  return title.english || title.romaji || title.native || null
}

function getSubtitle(title) {
  if (!title || typeof title === 'string') return null
  if (title.english && title.romaji && title.english !== title.romaji) return title.romaji
  return null
}

export default function AnimeCard({ anime, onDismiss, onAvoid, userProgress }) {
  const [expanded, setExpanded] = useState(false)
  const [imgError, setImgError] = useState(false)

  // Normalize the anime data — handle both nested API format and flat test format
  const data = anime?.anime ?? anime ?? {}
  const a = {
    id: data.id ?? anime?.id,
    idMal: data.idMal ?? anime?.idMal,
    externalLinks: data.externalLinks ?? anime?.externalLinks ?? [],
    title: data.title ?? anime?.title,
    genres: data.genres ?? anime?.genres ?? [],
    tags: data.tags ?? anime?.tags ?? [],
    studios: data.studios ?? anime?.studios ?? [],
    coverImage: data.coverImage ?? anime?.coverImage ?? anime?.cover_image,
    score: data.meanScore ?? data.averageScore ?? anime?.score ?? anime?.meanScore,
    episodes: data.episodes ?? anime?.episodes,
    season: data.season ?? anime?.season,
    seasonYear: data.seasonYear ?? anime?.seasonYear,
    format: data.format ?? anime?.format,
    status: data.status ?? anime?.status,
    synopsis: data.synopsis ?? data.description ?? anime?.synopsis,
    matchScore: anime?.matchScore,
    matchReason: anime?.matchReason,
  }

  const displayTitle = getTitle(a.title) || 'Unknown Title'
  const subTitle = getSubtitle(a.title)
  const coverUrl = typeof a.coverImage === 'string' ? a.coverImage : a.coverImage?.large || a.coverImage?.medium

  // Streaming links from AniList externalLinks
  const streamingLinks = (a.externalLinks || [])
    .filter(l => l.type === 'STREAMING')
    .slice(0, 5)

  // Episode progress from user's list
  const episodesTotal = a.episodes || anime?.episodes

  // Extract genre names, tag names, studio names
  const genreNames = a.genres.map(g => typeof g === 'string' ? g : g.name || g.genre).filter(Boolean)
  const tagNames = a.tags.map(t => typeof t === 'string' ? t : t.name).filter(Boolean)
  const studioNames = a.studios.map(s => typeof s === 'string' ? s : s.name || s.studio).filter(Boolean)

  const seasonStr = a.season ? (a.seasonYear ? `${a.season} ${a.seasonYear}` : a.season) : null
  const badges = [a.episodes && `${a.episodes} eps`, seasonStr, a.format, a.status].filter(Boolean)

  return (
    <div className="cyber-card overflow-hidden group">
      <div className="flex flex-col sm:flex-row">
        {/* Cover */}
        <div className="relative w-full sm:w-36 h-48 sm:h-44 flex-shrink-0 overflow-hidden bg-[#0f0f1a]">
          <img
            src={imgError || !coverUrl ? PLACEHOLDER : coverUrl}
            alt={displayTitle}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={() => setImgError(true)}
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#14141f] via-transparent to-transparent sm:bg-gradient-to-r sm:from-transparent sm:to-[#14141f]" />
        </div>

        {/* Content */}
        <div className="flex-1 p-4 min-w-0 flex flex-col">
          {/* Title + Score */}
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="min-w-0">
              <h3 className="font-display text-base font-semibold text-white truncate">{displayTitle}</h3>
              {subTitle && <p className="text-xs text-gray-500 font-mono truncate mt-0.5">{subTitle}</p>}
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {a.score != null && (
                <div className={`px-2.5 py-1 rounded-lg bg-[#0f0f1a] border border-[#1e1e2e] ${scoreColor(formatScore(a.score))}`}>
                  <span className="font-mono text-sm font-bold">{formatScore(a.score)}</span>
                </div>
              )}
              {a.matchScore != null && (
                <div className="px-2 py-1 rounded-lg bg-purple-900/20 border border-purple-700/30">
                  <span className="font-mono text-[10px] text-purple-300">{a.matchScore.toFixed(0)}%</span>
                </div>
              )}
              {userProgress?.progress != null && (
                <div className="px-2 py-1 rounded-lg bg-blue-900/20 border border-blue-700/30">
                  <span className="font-mono text-[10px] text-blue-300">
                    Ep {userProgress.progress}{episodesTotal ? `/${episodesTotal}` : ''}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Match reason */}
          {a.matchReason && (
            <p className="text-[11px] text-purple-400/70 font-mono mb-2 italic">"{a.matchReason}"</p>
          )}

          {/* Badges */}
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {badges.map((b) => (
                <span key={b} className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-full bg-cyan-900/20 text-cyan-400 border border-cyan-700/30">{b}</span>
              ))}
            </div>
          )}

          {/* Genres */}
          {genreNames.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {genreNames.slice(0, 5).map((g) => (
                <span key={g} className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-purple-900/30 text-purple-300 border border-purple-700/30">{g}</span>
              ))}
              {genreNames.length > 5 && (
                <span className="px-2 py-0.5 text-[10px] font-mono text-gray-500 border border-[#1e1e2e]">+{genreNames.length - 5}</span>
              )}
            </div>
          )}

          {/* Expand */}
          {(a.synopsis || studioNames.length > 0 || tagNames.length > 0) && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs font-mono text-gray-500 hover:text-purple-400 transition-colors flex items-center gap-1 mb-2"
            >
              {expanded ? '▲ Collapse' : '▼ Expand'}
            </button>
          )}

          {/* Expanded */}
          {expanded && (
            <div className="space-y-2 mb-3 animate-fade-in">
              {a.synopsis && <p className="text-xs text-gray-400 leading-relaxed line-clamp-4">{a.synopsis}</p>}
              {studioNames.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-[10px] font-mono text-gray-500 uppercase">Studios:</span>
                  {studioNames.map((s) => <span key={s} className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-blue-900/20 text-blue-400 border border-blue-700/30">{s}</span>)}
                </div>
              )}
              {tagNames.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {tagNames.slice(0, 8).map((t) => <span key={t} className="px-1.5 py-0.5 text-[9px] font-mono text-gray-500 border border-[#1e1e2e]">#{t}</span>)}
                </div>
              )}
            </div>
          )}

          {/* Streaming badges */}
          {streamingLinks.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {streamingLinks.slice(0, 5).map(l => (
                <a
                  key={l.site}
                  href={l.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-green-900/20 text-green-400 border border-green-700/30 hover:bg-green-900/40 transition-all"
                  title={`Watch on ${l.site}`}
                >
                  ▶ {l.site}
                </a>
              ))}
              {streamingLinks.length > 5 && (
                <span className="px-2 py-0.5 text-[10px] font-mono text-gray-500">+{streamingLinks.length - 5}</span>
              )}
              {a.idMal && (
              <a
                href={`https://anilist.co/anime/${a.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-amber-900/20 text-amber-400 border border-amber-700/30 hover:bg-amber-900/40 transition-all"
                title="View on AniList — MALSync shows 90+ streaming sites there"
              >
                ⊞ MALSync (90+)
              </a>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-center gap-2 mt-auto pt-3 border-t border-[#1e1e2e] flex-wrap">
            {a.idMal && (
              <a
                href={`https://anilist.co/anime/${a.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#1e1e2e] text-gray-500 hover:text-cyan-400 hover:border-cyan-500/40 transition-all whitespace-nowrap"
                title="View on AniList"
              >
                ▲ AniList
                <span className="ml-1 text-[8px] opacity-60">MALSync</span>
              </a>
            )}
            <a
              href={`https://myanimelist.net/anime/${a.idMal || a.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#1e1e2e] text-gray-500 hover:text-orange-400 hover:border-orange-500/40 transition-all whitespace-nowrap"
              title="View on MyAnimeList"
            >
              ● MAL
            </a>
            <button
              onClick={() => onDismiss?.(a.id)}
              className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#1e1e2e] text-gray-500 hover:text-pink-400 hover:border-pink-500/40 transition-all whitespace-nowrap"
            >
              ✕ Dismiss
            </button>
            <button
              onClick={() => genreNames.forEach(g => onAvoid?.(g))}
              className="px-3 py-1.5 text-xs font-mono rounded-lg border border-[#1e1e2e] text-gray-500 hover:text-blue-400 hover:border-blue-500/40 transition-all whitespace-nowrap"
            >
              ⊘ Avoid
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
