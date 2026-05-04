import { useState } from 'react'
import FilterControls from './FilterControls'

const GENRES = [
  'Action', 'Adventure', 'Comedy', 'Drama', 'Fantasy', 'Horror',
  'Mystery', 'Romance', 'Sci-Fi', 'Slice of Life', 'Sports',
  'Thriller', 'Psychological', 'Mecha', 'Music', 'Supernatural',
]

export default function DirectMode({ onRecommend, loading, avoidList = [] }) {
  const [selectedGenres, setSelectedGenres] = useState([])
  const [brainPower, setBrainPower] = useState(50)
  const [timeCommitment, setTimeCommitment] = useState('')
  const [moodIntent, setMoodIntent] = useState('')
  const [localAvoid, setLocalAvoid] = useState([])

  const toggleGenre = (genre) => {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (selectedGenres.length === 0) return
    onRecommend?.({
      genres: selectedGenres,
      brainPower,
      timeCommitment,
      moodIntent,
      avoidList: [...new Set([...localAvoid, ...avoidList])],
    })
  }

  return (
    <div className="cyber-card p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-lg">🎯</span>
        <h2 className="font-display text-sm font-semibold text-white">Direct Mode</h2>
      </div>

      {/* Genre Grid */}
      <div>
        <p className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-3">Genres</p>
        <div className="flex flex-wrap gap-2">
          {GENRES.map((genre) => {
            const selected = selectedGenres.includes(genre)
            return (
              <button
                key={genre}
                onClick={() => toggleGenre(genre)}
                className={`px-3 py-1.5 text-xs font-mono rounded-lg border transition-all duration-200 ${
                  selected
                    ? 'bg-blue-900/30 border-blue-500/50 text-blue-300'
                    : 'bg-[#0f0f1a] border-[#1e1e2e] text-gray-400 hover:border-purple-500/30 hover:text-gray-300'
                }`}
              >
                {genre}
              </button>
            )
          })}
        </div>
        {selectedGenres.length > 0 && (
          <p className="text-[10px] font-mono text-gray-500 mt-2">{selectedGenres.length} selected</p>
        )}
      </div>

      {/* Filters */}
      <FilterControls
        brainPower={brainPower}
        onBrainPowerChange={setBrainPower}
        timeCommitment={timeCommitment}
        onTimeCommitmentChange={setTimeCommitment}
        moodIntent={moodIntent}
        onMoodIntentChange={setMoodIntent}
        avoidList={[...new Set([...localAvoid, ...avoidList])]}
        onAvoidListChange={setLocalAvoid}
        showMoodIntent={true}
      />

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={selectedGenres.length === 0 || loading}
        className="cyber-button w-full text-sm py-4 flex items-center justify-center gap-2"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Computing...
          </span>
        ) : (
          <span>Get Recommendations</span>
        )}
      </button>
    </div>
  )
}

export { GENRES }
