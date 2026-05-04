const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  }
  const response = await fetch(url, config)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `API error: ${response.status}`)
  }
  return response.json()
}

// --- Anime List Import ---
export function fetchAnilist(username) {
  const ua = username || ''
  return request(`/api/anilist/fetch`, { method: 'POST', body: JSON.stringify({ username: ua }) })
}

export function fetchJikan(username) {
  const ua = username || ''
  return request(`/api/jikan/fetch`, { method: 'POST', body: JSON.stringify({ username: ua }) })
}

// --- Anime Details ---
export function getAnimeDetail(animeId) {
  return request(`/api/anime/${animeId}`)
}

// --- Taste Profile ---
export function fetchTasteProfile(username, source = 'anilist') {
  return request(`/api/profile/taste?username=${encodeURIComponent(username)}&source=${source}`)
}

// --- Recommendations ---
export function getMoodRecs(payload) {
  return request('/api/recommendations/mood', { method: 'POST', body: JSON.stringify(payload) })
}

export function getDirectRecs(payload) {
  return request('/api/recommendations/direct', { method: 'POST', body: JSON.stringify(payload) })
}

export function getFallbackRecs(payload) {
  return request('/api/recommendations', { method: 'POST', body: JSON.stringify(payload) })
}

// --- Search History ---
export function getSearchHistory() {
  return request('/api/search/history')
}

export function saveSearchHistory(payload) {
  return request('/api/search/history', { method: 'POST', body: JSON.stringify(payload) })
}

export function loadSearch(id) {
  return request(`/api/search/history/${id}`)
}

// --- Legacy aliases (for existing components) ---
export const fetchSearchHistory = getSearchHistory

export default {
  fetchAnilist,
  fetchJikan,
  getAnimeDetail,
  fetchTasteProfile,
  getMoodRecs,
  getDirectRecs,
  getFallbackRecs,
  getSearchHistory,
  fetchSearchHistory,
  saveSearchHistory,
  loadSearch,
}
