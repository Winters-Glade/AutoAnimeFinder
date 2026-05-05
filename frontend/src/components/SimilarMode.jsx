import { useState, useRef, useEffect } from 'react'
import AnimeCard from './AnimeCard'
import NeuralLoader from './NeuralLoader'
import { getSimilarRecs } from '../api/client'

export default function SimilarMode({ username, source, watchedIds, episodeMap,
                                       onDismiss, onAvoid }) {
  const [inputValue, setInputValue] = useState('')
  const [seeds, setSeeds] = useState([])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [fetched, setFetched] = useState(false)

  const debounceRef = useRef(null)

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [])

  // Search anime as user types (debounced 300ms)
  const handleSearch = (query) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query || query.length < 2) {
      setSearchResults([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=10`)
        const json = await res.json()
        setSearchResults(json.results || json.anime || [])
      } catch (e) {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
  }

  const addSeed = (anime) => {
    if (seeds.length >= 5) return
    if (seeds.find(s => s.id === anime.id)) return
    setSeeds([...seeds, anime])
    setInputValue('')
    setSearchResults([])
  }

  const removeSeed = (id) => {
    setSeeds(seeds.filter(s => s.id !== id))
  }

  const findSimilar = async () => {
    if (seeds.length === 0) return
    setLoading(true)
    setError(null)
    setFetched(false)
    try {
      const data = await getSimilarRecs({ seedIds: seeds.map(s => s.id), limit: 24, source })
      setResults(data.recommendations || [])
      setFetched(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Filter out anime the user has already completed (but keep CURRENT, PLANNING, PAUSED, etc.)
  const filteredResults = results.filter(
    r => !(r.anime?.id && episodeMap?.[r.anime.id]?.status === 'COMPLETED')
  )

  return (
    <div>
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
          🎯 If You Liked...
        </h2>
        <p className="text-gray-400 text-sm mt-1">
          Enter 1-5 anime and find similar shows you'll love
        </p>
      </div>

      {/* Seed input */}
      <div className="max-w-xl mx-auto mb-6">
        <div className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value)
              handleSearch(e.target.value)
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch(inputValue)}
            placeholder="Search for an anime..."
            className="w-full px-4 py-3 rounded-lg bg-gray-800/70 border border-gray-700
                       text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500
                       transition-colors"
            disabled={seeds.length >= 5}
          />

          {/* Search suggestions dropdown */}
          {searchResults.length > 0 && inputValue.length >= 2 && (
            <div className="absolute z-20 top-full left-0 right-0 mt-1
                            bg-gray-800 border border-gray-700 rounded-lg
                            max-h-48 overflow-y-auto shadow-xl">
              {searchResults.map(anime => (
                <button
                  key={anime.id}
                  onClick={() => addSeed(anime)}
                  className="w-full text-left px-4 py-2 hover:bg-gray-700
                             text-sm text-gray-200 flex items-center gap-3 transition-colors"
                >
                  <span className="text-base">{anime.title?.romaji || anime.title?.english || `#${anime.id}`}</span>
                  <span className="text-xs text-gray-500 ml-auto">
                    {anime.genres?.slice(0, 2).join(', ')}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Selected seeds */}
        {seeds.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {seeds.map(anime => (
              <span
                key={anime.id}
                className="inline-flex items-center gap-1.5 px-3 py-1.5
                           bg-cyan-900/40 border border-cyan-700/50 rounded-full
                           text-sm text-cyan-200"
              >
                {anime.title?.romaji || anime.title?.english || `#${anime.id}`}
                <button
                  onClick={() => removeSeed(anime.id)}
                  className="text-cyan-400 hover:text-red-400 transition-colors ml-1"
                >
                  ✕
                </button>
              </span>
            ))}
            <span className="text-xs text-gray-500 self-center ml-2">
              {seeds.length}/5
            </span>
          </div>
        )}

        {/* Find Similar button */}
        <button
          onClick={findSimilar}
          disabled={seeds.length === 0 || loading}
          className="mt-4 w-full px-6 py-3 rounded-lg text-sm font-medium transition-all
                     bg-gradient-to-r from-cyan-600 to-blue-600 text-white
                     hover:from-cyan-500 hover:to-blue-500
                     disabled:opacity-40 disabled:cursor-not-allowed
                     shadow-lg shadow-cyan-900/30"
        >
          {loading ? '⟳ Finding Similar...' : '🎯 Find Similar'}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="mt-4">
          <NeuralLoader />
          <p className="text-center text-gray-500 text-sm mt-2">Finding similar anime...</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="max-w-lg mx-auto mb-6 p-3 bg-amber-900/30 border border-amber-700/50 rounded-lg text-amber-300 text-sm text-center">
          ⚠️ {error}
        </div>
      )}

      {/* No results */}
      {!loading && fetched && !error && filteredResults.length === 0 && (
        <div className="text-center py-12">
          <div className="text-5xl mb-4">🔍</div>
          <h3 className="text-xl font-semibold text-gray-300 mb-2">No similar anime found</h3>
          <p className="text-gray-500 text-sm">Try different anime or add more seeds</p>
        </div>
      )}

      {/* Results */}
      {!loading && filteredResults.length > 0 && (
        <div>
          <h3 className="text-lg neon-text mb-4 flex items-center gap-2">
            ✨ Similar Anime
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
