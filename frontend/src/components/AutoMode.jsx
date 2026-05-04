import { useState, useEffect, useCallback } from 'react'
import AnimeCard from './AnimeCard'
import NeuralLoader from './NeuralLoader'
import { getAutoRecs } from '../api/client'

export default function AutoMode({ username, source, onRecommend, onDismiss, onAvoid,
                                    recommendations, loading, error, watchedIds, episodeMap }) {
  const [localResults, setLocalResults] = useState([])
  const [localLoading, setLocalLoading] = useState(false)
  const [localError, setLocalError] = useState(null)
  const [fetched, setFetched] = useState(false)

  // Use parent's recommendations if provided, otherwise local
  const results = recommendations?.length ? recommendations : localResults
  const isLoading = loading || localLoading
  const errMsg = error || localError

  const fetchAuto = useCallback(async () => {
    if (!username) return
    setLocalLoading(true)
    setLocalError(null)
    try {
      const data = await getAutoRecs({ username, source, limit: 24, seedCount: 5 })
      if (data?.recommendations?.length) {
        // Normalize response: might be { recommendations: [...] } or plain array
        setLocalResults(data.recommendations.map(r => r.anime ? r : { anime: r }))
      } else {
        setLocalError('No auto-recommendations found. Try rating more anime on your AniList!')
      }
    } catch (e) {
      setLocalError(e.message)
    } finally {
      setLocalLoading(false)
      setFetched(true)
    }
  }, [username, source])

  // Auto-fetch on mount when username is available
  useEffect(() => {
    if (username && !fetched && !localLoading) {
      fetchAuto()
    }
  }, [username, fetched, localLoading, fetchAuto])

  // Reset when username changes
  useEffect(() => {
    setLocalResults([])
    setFetched(false)
    setLocalError(null)
  }, [username])

  const filteredResults = results.filter(
    r => !(r.anime?.id && watchedIds?.has(r.anime.id))
  )

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
          ⚡ Auto Mode
        </h2>
        <p className="text-gray-400 text-sm mt-1">
          Zero effort — based on your recent high-rated completed anime
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-4 mb-8">
        <button
          onClick={fetchAuto}
          disabled={isLoading || !username}
          className="px-6 py-2.5 rounded-lg text-sm font-medium transition-all
                     bg-gradient-to-r from-cyan-600 to-blue-600 text-white
                     hover:from-cyan-500 hover:to-blue-500
                     disabled:opacity-40 disabled:cursor-not-allowed
                     shadow-lg shadow-cyan-900/30"
        >
          {isLoading ? '⟳ Analyzing...' : '⟳ Refresh'}
        </button>
        {fetched && !isLoading && localResults.length > 0 && (
          <span className="text-xs text-gray-500">
            Based on your last {Math.min(5, localResults.length)} recently completed favorites
          </span>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="mt-4">
          <NeuralLoader />
          <p className="text-center text-gray-500 text-sm mt-2">
            Scanning your completed anime for the perfect matches...
          </p>
        </div>
      )}

      {/* Error */}
      {errMsg && !isLoading && (
        <div className="max-w-lg mx-auto mb-6 p-3 bg-amber-900/30 border border-amber-700/50 rounded-lg text-amber-300 text-sm text-center">
          ⚠️ {errMsg}
        </div>
      )}

      {/* No results */}
      {!isLoading && fetched && !errMsg && filteredResults.length === 0 && (
        <div className="text-center py-12">
          <div className="text-5xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold text-gray-300 mb-2">No recommendations yet</h3>
          <p className="text-gray-500 text-sm">
            Import your AniList above to get personalized auto-recommendations!
          </p>
        </div>
      )}

      {/* Results grid */}
      {!isLoading && filteredResults.length > 0 && (
        <div>
          <h3 className="text-lg neon-text mb-4 flex items-center gap-2">
            ✨ Picks for You
            <span className="text-sm text-gray-400 font-normal">
              ({filteredResults.length} matches)
            </span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filteredResults.map((item) => {
              const anime = item.anime ?? item
              return (
                <AnimeCard
                  key={anime.id}
                  anime={item}
                  userProgress={episodeMap[anime.id]}
                  onDismiss={onDismiss}
                  onAvoid={onAvoid}
                />
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
