import { useState, useEffect } from 'react'
import { fetchSearchHistory, loadSearch } from '../api/client'

export default function SearchHistory({ onLoadSearch }) {
  const [searches, setSearches] = useState([])
  const [loading, setLoading] = useState(false)

  const loadHistory = async () => {
    setLoading(true)
    try {
      const data = await fetchSearchHistory()
      setSearches(Array.isArray(data) ? data : [])
    } catch {
      // Backend not ready
    }
    setLoading(false)
  }

  useEffect(() => { loadHistory() }, [])

  const handleLoad = async (id) => {
    try {
      const search = await loadSearch(id)
      onLoadSearch?.(search)
    } catch {
      // fail silently
    }
  }

  const formatTime = (ts) => {
    const d = new Date(ts)
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div>
      <h3 className="text-xs font-mono text-gray-400 uppercase tracking-wider mb-3">Search History</h3>

      {searches.length === 0 ? (
        <p className="text-xs font-mono text-gray-500 text-center py-6">
          {loading ? 'Loading...' : 'No saved searches yet'}
        </p>
      ) : (
        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {searches.map((search) => (
            <button
              key={search.id}
              onClick={() => handleLoad(search.id)}
              className="w-full text-left cyber-card p-2.5 transition-all duration-200"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-mono text-gray-300 truncate">
                  {search.query || search.mood || 'Direct search'}
                </span>
                <span className="text-[10px] font-mono text-gray-500 shrink-0">{formatTime(search.created_at)}</span>
              </div>
              {search.mode && (
                <span className="text-[10px] font-mono text-purple-400 mt-0.5 inline-block">{search.mode}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
