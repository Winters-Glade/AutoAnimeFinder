import { useState, useEffect } from 'react'
import Header from '../components/Header'
import MoodTranslator from '../components/MoodTranslator'
import DirectMode from '../components/DirectMode'
import TasteProfile from '../components/TasteProfile'
import SearchHistory from '../components/SearchHistory'
import AnimeCard from '../components/AnimeCard'
import NeuralLoader from '../components/NeuralLoader'
import { fetchAnilist, fetchTasteProfile, getMoodRecs, getDirectRecs,
         getSearchHistory, saveSearchHistory } from '../api/client'

export default function HomePage() {
  const [username, setUsername] = useState('')
  const [source, setSource] = useState('anilist')
  const [activeTab, setActiveTab] = useState('mood')
  const [tasteProfile, setTasteProfile] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const [avoidList, setAvoidList] = useState([])
  const [dismissedIds, setDismissedIds] = useState(new Set())

  useEffect(() => { loadHistory() }, [])

  const handleImport = async () => {
    if (!username.trim()) return
    setProfileLoading(true)
    setError(null)
    try {
      await fetchAnilist(username)
      const profile = await fetchTasteProfile(username, source)
      setTasteProfile(profile)
    } catch (e) {
      setError(e.message || 'Failed to import anime list')
    } finally {
      setProfileLoading(false)
    }
  }

  const handleMoodRec = async (filters) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getMoodRecs({ username, source, ...filters })
      const results = data?.recommendations ?? data ?? []
      if (!Array.isArray(results)) return setError('Invalid response from server')
      setRecommendations(results.filter(r => !dismissedIds.has(r.id)))
      await saveSearchHistory({ query: filters.moodQuery || '(mood)', type: 'mood', filters })
      loadHistory()
    } catch (e) {
      setError(e.message || 'Failed to get recommendations')
    } finally {
      setLoading(false)
    }
  }

  const handleDirectRec = async (filters) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getDirectRecs({ username, source, ...filters })
      const results = data?.recommendations ?? data ?? []
      if (!Array.isArray(results)) return setError('Invalid response from server')
      setRecommendations(results.filter(r => !dismissedIds.has(r.id)))
      await saveSearchHistory({ query: `Direct: ${(filters.genres || []).join(', ')}`, type: 'direct', filters })
      loadHistory()
    } catch (e) {
      setError(e.message || 'Failed to get recommendations')
    } finally {
      setLoading(false)
    }
  }

  const handleDismiss = (id) => {
    setDismissedIds(prev => new Set([...prev, id]))
    setRecommendations(prev => prev.filter(r => r.id !== id))
  }

  const handleAvoid = (genre) => {
    if (!avoidList.includes(genre)) setAvoidList(prev => [...prev, genre])
  }

  const loadHistory = async () => {
    try {
      const h = await getSearchHistory()
      setHistory(Array.isArray(h) ? h : [])
    } catch { /* ignore */ }
  }

  const handleLoadSearch = (search) => {
    if (!search) return
    if (search.type === 'mood' && search.filters) handleMoodRec(search.filters)
    else if (search.type === 'direct' && search.filters) handleDirectRec(search.filters)
  }

  const filteredResults = Array.isArray(recommendations) ? recommendations.filter(r => !dismissedIds.has(r.id)) : []

  return (
    <div className="min-h-screen bg-[#0a0a14] text-white">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero */}
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold neon-text mb-2 tracking-wider">
            ✦ ANIME SOUL WHISPER ✦
          </h1>
          <p className="text-gray-400 text-sm md:text-base">
            Your AI-powered anime discovery engine
          </p>
        </div>

        {/* Import Section */}
        <div className="cyber-card p-4 mb-8 flex flex-wrap items-center gap-3 justify-center">
          <input
            className="cyber-input px-4 py-2 w-48 text-sm"
            placeholder="AniList username..."
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleImport()}
          />
          <select
            className="cyber-input px-3 py-2 text-sm bg-gray-900"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="anilist">AniList</option>
            <option value="mal">MyAnimeList</option>
          </select>
          <button
            className="cyber-button px-6 py-2 text-sm"
            onClick={handleImport}
            disabled={profileLoading || !username.trim()}
          >
            {profileLoading ? '⌛ Importing...' : '🔮 Import'}
          </button>
        </div>

        {error && (
          <div className="max-w-xl mx-auto mb-6 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm text-center">
            ⚠️ {error}
          </div>
        )}

        {/* Tab Switcher */}
        <div className="flex gap-2 mb-6 justify-center">
          <button
            onClick={() => setActiveTab('mood')}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'mood'
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-purple-900/30'
                : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
            }`}
          >
            🌙 Mood Translator
          </button>
          <button
            onClick={() => setActiveTab('direct')}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'direct'
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-purple-900/30'
                : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
            }`}
          >
            🎯 Direct Mode
          </button>
        </div>

        {/* Main Layout */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Column */}
          <div className="flex-1 min-w-0">
            {activeTab === 'mood' ? (
              <MoodTranslator onRecommend={handleMoodRec} loading={loading} avoidList={avoidList} />
            ) : (
              <DirectMode onRecommend={handleDirectRec} loading={loading} avoidList={avoidList} />
            )}

            {loading && (
              <div className="mt-8"><NeuralLoader /></div>
            )}

            {!loading && filteredResults.length > 0 && (
              <div className="mt-6">
                <h2 className="text-xl neon-text mb-4 flex items-center gap-2">
                  ✨ Recommendations
                  <span className="text-sm text-gray-400 font-normal">({filteredResults.length} found)</span>
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {filteredResults.map((anime) => (
                    <AnimeCard
                      key={anime.id}
                      anime={anime}
                      onDismiss={() => handleDismiss(anime.id)}
                      onAvoid={() => anime.genres?.forEach((g) => handleAvoid(g))}
                    />
                  ))}
                </div>
              </div>
            )}

            {!loading && recommendations.length > 0 && filteredResults.length === 0 && (
              <div className="mt-8 text-center text-gray-500">
                All recommendations dismissed.{' '}
                <button className="text-blue-400 hover:text-blue-300 underline" onClick={() => setDismissedIds(new Set())}>
                  Reset dismissals
                </button>
              </div>
            )}

            {!loading && !error && recommendations.length === 0 && (
              <div className="mt-8 text-center text-gray-500 text-sm">
                {activeTab === 'mood'
                  ? 'Describe your mood above to discover anime'
                  : 'Select genres and filters to get started'}
              </div>
            )}
          </div>

          {/* Right Sidebar */}
          <div className="w-full lg:w-72 space-y-4 shrink-0">
            <TasteProfile profile={tasteProfile} loading={profileLoading} />
            <SearchHistory onLoadSearch={handleLoadSearch} />
          </div>
        </div>
      </main>

      <footer className="text-center py-8 text-gray-600 text-xs">
        <div className="max-w-7xl mx-auto px-4">
          Anime Soul Whisper &mdash; Powered by{' '}
          <a href="https://anilist.co" className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">AniList</a>
          {' & '}
          <a href="https://myanimelist.net" className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">MyAnimeList</a>
        </div>
      </footer>
    </div>
  )
}
