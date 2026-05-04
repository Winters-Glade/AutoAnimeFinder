import { useState } from 'react'
import FilterControls from './FilterControls'

export default function MoodTranslator({ onRecommend, loading, avoidList = [] }) {
  const [moodQuery, setMoodQuery] = useState('')
  const [brainPower, setBrainPower] = useState(50)
  const [timeCommitment, setTimeCommitment] = useState('')
  const [moodIntent, setMoodIntent] = useState('')
  const [localAvoid, setLocalAvoid] = useState([])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!moodQuery.trim()) return
    onRecommend?.({
      moodQuery: moodQuery.trim(),
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
        <span className="text-lg">🌙</span>
        <h2 className="font-display text-sm font-semibold text-white">Mood Translator</h2>
      </div>

      {/* Mood Input */}
      <div>
        <p className="text-[10px] font-mono text-cyber-muted uppercase tracking-wider mb-2">
          Describe the vibe you're looking for...
        </p>
        <textarea
          value={moodQuery}
          onChange={(e) => setMoodQuery(e.target.value)}
          placeholder='e.g. "Something dark and psychological after a bad day"'
          rows={3}
          className="cyber-input resize-none text-sm placeholder:text-gray-600"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e)
          }}
        />
        <p className="text-[10px] font-mono text-cyber-muted mt-1">
          ⌘+Enter to submit
        </p>
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

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!moodQuery.trim() || loading}
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
          <span>🔮 DISCOVER PERFECT MATCH</span>
        )}
      </button>
    </div>
  )
}
