import { useState, useEffect } from 'react'
import Header from '../components/Header'
import AutoMode from '../components/AutoMode'
import SimilarMode from '../components/SimilarMode'
import MoodTranslator from '../components/MoodTranslator'
import DirectMode from '../components/DirectMode'
import TasteProfile from '../components/TasteProfile'
import SearchHistory from '../components/SearchHistory'
import AnimeCard from '../components/AnimeCard'
import NeuralLoader from '../components/NeuralLoader'
import { fetchAnilist, fetchTasteProfile, getAutoRecs, getSimilarRecs, getMoodRecs, getDirectRecs,
         getSearchHistory, saveSearchHistory } from '../api/client'

export default function HomePage() {
  const [username, setUsername] = useState('')
  const [source, setSource] = useState('anilist')
  const [activeTab, setActiveTab] = useState('auto')
  const [tasteProfile, setTasteProfile] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const [avoidList, setAvoidList] = useState([])
  const [dismissedIds, setDismissedIds] = useState(new Set())
  const [watchedIds, setWatchedIds] = useState(new Set()) // anime the user has already seen
  const [episodeMap, setEpisodeMap] = useState({}) // { [animeId]: { progress, status } }
  const [showMalsyncPrompt, setShowMalsyncPrompt] = useState(true) // MALSync promotion

  useEffect(() => { loadHistory() }, [])

  // Best-effort MALSync detection (may not work in all browsers)
  useEffect(() => {
    // Chrome: try to ping the extension
    if (typeof chrome !== 'undefined' && chrome.runtime?.sendMessage) {
      chrome.runtime.sendMessage(
        'jgddhcdhccphnhbnhggnkjbkcloeclfb',
        { type: 'PING' },
        (res) => { if (res) setShowMalsyncPrompt(false) }
      )
    }
    // Firefox: try alternative detection
    if (typeof browser !== 'undefined' && browser.runtime?.sendMessage) {
      browser.runtime.sendMessage(
        'malsync@malsync',
        { type: 'PING' },
        (res) => { if (res) setShowMalsyncPrompt(false) }
      )
    }
  }, [])

  // Auto-import on mount if a username was previously saved
  useEffect(() => {
    const saved = localStorage.getItem('aionrs_username')
    if (saved) {
      setUsername(saved)
      // Small delay so state is set before fetch
      const timer = setTimeout(() => {
        const el = document.querySelector('input[placeholder="AniList username..."]')
        if (el) el.value = saved
        doImport(saved)
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [])

  const doImport = async (name) => {
    if (!name?.trim()) return
    setProfileLoading(true)
    setError(null)
    try {
      const data = await fetchAnilist(name)
      const animeList = data?.animeList ?? data?.anime ?? []
      const seen = new Set(
        animeList
          .filter(a => a.status !== 'PLANNING' && a.status !== 'planning')
          .map(a => a.anime?.id ?? a.mediaId ?? a.media_id)
          .filter(Boolean)
      )
      // Build episode progress map
      const epMap = {}
      animeList.forEach(a => {
        const aid = a.anime?.id
        if (aid) epMap[aid] = { progress: a.progress, status: a.status }
      })
      console.log('Excluding', seen.size, 'watched anime from recommendations')
      setWatchedIds(seen)
      setEpisodeMap(epMap)
      const profile = await fetchTasteProfile(name, source)
      setTasteProfile(profile)
    } catch (e) {
      setError(e.message || 'Failed to import anime list')
    } finally {
      setProfileLoading(false)
    }
  }

  const handleImport = async () => {
    if (!username.trim()) return
    localStorage.setItem('aionrs_username', username.trim())
    await doImport(username.trim())
  }

  const excludeList = [...new Set([...watchedIds, ...dismissedIds].filter(id => id != null && !isNaN(id)))]

  const handleMoodRec = async (filters) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getMoodRecs({ username, source, excludeList, ...filters })
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
      const data = await getDirectRecs({ username, source, excludeList, ...filters })
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
    if (id == null) return
    const numId = Number(id)
    if (isNaN(numId)) return
    setDismissedIds(prev => new Set([...prev, numId]))
    setRecommendations(prev => prev.filter(r => (r.anime?.id ?? r.id) !== numId))
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

          {/* MALSync promotion */}
          {showMalsyncPrompt && (
            <div className="mb-4 px-4 py-2 rounded-lg bg-amber-900/20 border border-amber-700/30 text-amber-300 text-xs inline-flex items-center gap-2">
              <span>💡</span>
              <span>
                Install{' '}
                <a href="https://github.com/MALSync/MALSync" target="_blank" rel="noopener noreferrer" className="underline hover:text-amber-200">
                  MALSync
                </a>
                {' '}to auto-sync your AniList/MAL across 90+ streaming sites
              </span>
              <button onClick={() => setShowMalsyncPrompt(false)} className="ml-2 px-1.5 hover:text-amber-200">&times;</button>
            </div>
          )}

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
            ⚠️ {typeof error === 'string' ? error : 'An unexpected error occurred'}
          </div>
        )}

        {/* Tab Switcher */}
        <div className="flex gap-2 mb-6 justify-center flex-wrap">
          <button
            onClick={() => setActiveTab('auto')}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'auto'
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-900/30'
                : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
            }`}
          >
            ⚡ Auto
          </button>
          <button
            onClick={() => setActiveTab('similar')}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'similar'
                ? 'bg-gradient-to-r from-green-600 to-teal-600 text-white shadow-lg shadow-green-900/30'
                : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
            }`}
          >
            🔍 If You Liked...
          </button>
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
            {activeTab === 'auto' ? (
              <AutoMode
                username={username}
                source={source}
                recommendations={recommendations}
                loading={loading}
                error={error}
                watchedIds={watchedIds}
                episodeMap={episodeMap}
                onDismiss={(id) => handleDismiss(id)}
                onAvoid={handleAvoid}
              />
            ) : activeTab === 'similar' ? (
              <SimilarMode
                username={username}
                source={source}
                watchedIds={watchedIds}
                episodeMap={episodeMap}
                onDismiss={(id) => handleDismiss(id)}
                onAvoid={handleAvoid}
              />
            ) : activeTab === 'mood' ? (
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
                      key={anime.anime?.id ?? anime.id}
                      anime={anime}
                      userProgress={episodeMap[anime.anime?.id ?? anime.id]}
                      onDismiss={(id) => handleDismiss(id)}
                      onAvoid={handleAvoid}
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
                  : activeTab === 'similar'
                  ? 'Search for anime above to find similar shows'
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
