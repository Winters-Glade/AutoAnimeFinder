import { useState } from 'react'

const BRAIN_POWER_LABELS = ['Minimal', 'Light', 'Moderate', 'Deep', 'Maximum']
const BRAIN_POWER_COLORS = ['#10b981', '#22d3ee', '#00d4ff', '#a855f7', '#ec4899']

const TIME_COMMITMENTS = [
  { value: 'quick', label: 'Quick (<10 eps)' },
  { value: 'session', label: 'Session (1 cour)' },
  { value: 'commitment', label: 'Commitment (2+ cours)' },
  { value: 'ongoing', label: 'Ongoing' },
]

const MOOD_INTENTS = [
  { value: 'escape', label: 'Escape Reality', emoji: '🌀' },
  { value: 'feel_better', label: 'Feel Better', emoji: '✨' },
  { value: 'lean_in', label: 'Lean Into It', emoji: '🔥' },
  { value: 'surprise', label: 'Surprise Me', emoji: '🎲' },
]

export default function FilterControls({
  brainPower,
  onBrainPowerChange,
  timeCommitment,
  onTimeCommitmentChange,
  moodIntent,
  onMoodIntentChange,
  avoidList = [],
  onAvoidListChange,
  showMoodIntent = true,
}) {
  const [avoidInput, setAvoidInput] = useState('')

  const addAvoid = () => {
    const tag = avoidInput.trim()
    if (tag && !avoidList.includes(tag)) {
      onAvoidListChange?.([...avoidList, tag])
      setAvoidInput('')
    }
  }

  const removeAvoid = (tag) => {
    onAvoidListChange?.(avoidList.filter((t) => t !== tag))
  }

  const handleAvoidKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addAvoid()
    }
  }

  return (
    <div className="space-y-6">
      {/* Brain Power Slider */}
      <div>
        <label className="flex items-center justify-between mb-2">
          <span className="font-mono text-xs text-gray-400 uppercase tracking-wider">Brain Power</span>
          <span
            className="font-mono text-xs font-bold"
            style={{ color: BRAIN_POWER_COLORS[Math.floor(((brainPower - 1) / 99) * 4)] || BRAIN_POWER_COLORS[0] }}
          >
            {BRAIN_POWER_LABELS[Math.floor(((brainPower - 1) / 99) * 4)] || 'Minimal'}
          </span>
        </label>
        <div className="relative pt-1">
          <div className="h-2 bg-[#0f0f1a] rounded-full overflow-hidden border border-[#1e1e2e]">
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${brainPower}%`,
                background: `linear-gradient(90deg, ${BRAIN_POWER_COLORS[0]}, ${BRAIN_POWER_COLORS[1]}, ${BRAIN_POWER_COLORS[2]}, ${BRAIN_POWER_COLORS[3]}, ${BRAIN_POWER_COLORS[4]})`,
              }}
            />
          </div>
          <input
            type="range"
            min="1"
            max="100"
            value={brainPower}
            onChange={(e) => onBrainPowerChange?.(Number(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>
      </div>

      {/* Time Commitment */}
      <div>
        <label className="block font-mono text-xs text-gray-400 uppercase tracking-wider mb-2">Time Commitment</label>
        <div className="grid grid-cols-2 gap-2">
          {TIME_COMMITMENTS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => onTimeCommitmentChange?.(value)}
              className={`px-3 py-2 text-xs font-mono rounded-lg border transition-all duration-200 ${
                timeCommitment === value
                  ? 'bg-purple-900/30 border-purple-500/60 text-purple-300'
                  : 'bg-[#0f0f1a] border-[#1e1e2e] text-gray-400 hover:border-purple-500/30 hover:text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Mood Intent */}
      {showMoodIntent && (
        <div>
          <label className="block font-mono text-xs text-gray-400 uppercase tracking-wider mb-2">Mood Intent</label>
          <div className="grid grid-cols-2 gap-2">
            {MOOD_INTENTS.map(({ value, label, emoji }) => (
              <button
                key={value}
                onClick={() => onMoodIntentChange?.(value)}
                className={`px-3 py-2 text-xs font-mono rounded-lg border transition-all duration-200 ${
                  moodIntent === value
                    ? 'bg-blue-900/30 border-blue-500/60 text-blue-300'
                    : 'bg-[#0f0f1a] border-[#1e1e2e] text-gray-400 hover:border-blue-500/30 hover:text-gray-300'
                }`}
              >
                {emoji} {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Avoid List */}
      <div>
        <label className="block font-mono text-xs text-gray-400 uppercase tracking-wider mb-2">Avoid List</label>
        {avoidList.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {avoidList.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-pink-900/20 border border-pink-700/30 text-pink-400 text-[10px] font-mono"
              >
                {tag}
                <button onClick={() => removeAvoid(tag)} className="hover:text-white transition-colors">✕</button>
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            value={avoidInput}
            onChange={(e) => setAvoidInput(e.target.value)}
            onKeyDown={handleAvoidKeyDown}
            placeholder="Add genre, studio, or tag..."
            className="flex-1 cyber-input text-xs"
          />
          <button
            onClick={addAvoid}
            disabled={!avoidInput.trim()}
            className="px-3 py-2 text-xs font-mono rounded-lg bg-[#0f0f1a] border border-[#1e1e2e] text-gray-500 hover:text-purple-400 hover:border-purple-500/40 transition-all disabled:opacity-40"
          >
            + Add
          </button>
        </div>
      </div>
    </div>
  )
}

export { TIME_COMMITMENTS, MOOD_INTENTS, BRAIN_POWER_LABELS, BRAIN_POWER_COLORS }
