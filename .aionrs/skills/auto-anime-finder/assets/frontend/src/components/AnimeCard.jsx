import { useState } from 'react'

const PLACEHOLDER = 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450" viewBox="0 0 300 450">
    <rect width="300" height="450" fill="#14141f"/>
    <text x="150" y="225" font-family="monospace" font-size="14" fill="#6b7280" text-anchor="middle" dominant-baseline="middle">No Image</text>
  </svg>`
)

function formatScore(s) {
  if (s == null) return null
  return typeof s === 'number' ? s.toFixed(1) : s
}

function scoreColor(s) {
  const n = parseFloat(s)
  if (n >= 8) return 'text-green-400'
  if (n >= 6) return 'text-cyan-400'
  if (n >= 4) return 'text-purple-400'
  return 'text-pink-400'
}

export default function AnimeCard({ anime, onDismiss, onAvoid }) {
  const [expanded, setExpanded] = useState(false)
  const [imgError, setImgError] = useState(false)

  const {
    id,
    title_romaji,
    title_english,
    cover_image,
    score,
    episodes,
    season,
    format,
    status,
    genres = [],
    synopsis,
    studios = [],
    tags = [],
  } = anime || {}

  const displayTitle = title_english || title_romaji || 'Unknown Title'
  const subTitle = title_english && title_romaji !== title_english ? title_romaji : null
  const badges = [episodes && `${episodes} eps`, season, format, status].filter(Boolean)

  return (
    <div className="cyber-card overflow-hidden group">
      <div className="flex flex-col sm:flex-row">
        {/* Cover */}
        <div className="relative w-full sm:w-36 h-48 sm:h-44 flex-shrink-0 overflow-hidden bg-[#0f0f1a]">
          <img
            src={imgError || !cover_image ? PLACEHOLDER : cover_image}
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
            {score != null && (
              <div className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#0f0f1a] border border-[#1e1e2e] ${scoreColor(score)}`}>
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span className="font-mono text-sm font-bold">{formatScore(score)}</span>
              </div>
            )}
          </div>

          {/* Badges */}
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {badges.map((b) => (
                <span key={b} className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-full bg-cyan-900/20 text-cyan-400 border border-cyan-700/30">{b}</span>
              ))}
            </div>
          )}

          {/* Genres */}
          {genres.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {genres.slice(0, 5).map((g) => (
                <span key={g} className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-purple-900/30 text-purple-300 border border-purple-700/30">{g}</span>
              ))}
              {genres.length > 5 && (
                <span className="px-2 py-0.5 text-[10px] font-mono text-gray-500 border border-[#1e1e2e]">+{genres.length - 5}</span>
              )}
            </div>
          )}

          {/* Expand */}
          {(synopsis || studios.length > 0 || tags.length > 0) && (
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
              {synopsis && <p className="text-xs text-gray-400 leading-relaxed line-clamp-4">{synopsis}</p>}
              {studios.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-[10px] font-mono text-gray-500 uppercase">Studios:</span>
                  {studios.map((s) => <span key={s} className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-blue-900/20 text-blue-400 border border-blue-700/30">{s}</span>)}
                </div>
              )}
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {tags.slice(0, 8).map((t) => <span key={t} className="px-1.5 py-0.5 text-[9px] font-mono text-gray-500 border border-[#1e1e2e]">#{t}</span>)}
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 mt-auto pt-3 border-t border-[#1e1e2e]">
            <button
              onClick={() => onDismiss?.(id)}
              className="flex-1 px-3 py-1.5 text-xs font-mono rounded-lg border border-[#1e1e2e] text-gray-500 hover:text-pink-400 hover:border-pink-500/40 transition-all"
            >
              ✕ Dismiss
            </button>
            <button
              onClick={() => onAvoid?.(id)}
              className="flex-1 px-3 py-1.5 text-xs font-mono rounded-lg border border-[#1e1e2e] text-gray-500 hover:text-blue-400 hover:border-blue-500/40 transition-all"
            >
              ⊘ Avoid
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
