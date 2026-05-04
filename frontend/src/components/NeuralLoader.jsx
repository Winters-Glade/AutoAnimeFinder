import { useState, useEffect } from 'react'

const MESSAGES = [
  'Analyzing your soul\'s frequency...',
  'Consulting the anime oracle...',
  'Decoding your anime DNA...',
  'Scanning the multiverse for matches...',
  'Syncing with the celestial database...',
  'Channeling your inner protagonist...',
  'Calculating emotional resonance...',
  'Searching for hidden gems...',
]

export default function NeuralLoader({ message, className = '' }) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((i) => (i + 1) % MESSAGES.length)
    }, 2500)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={`flex flex-col items-center justify-center gap-6 py-16 ${className}`}>
      {/* Neural Orb */}
      <div className="relative w-20 h-20">
        <div className="absolute inset-0 rounded-full border-2 border-[#1e1e2e] animate-pulse" />
        <div className="absolute inset-1 rounded-full border-2 border-transparent border-t-blue-500 border-r-purple-500 animate-spin" />
        <div className="absolute inset-3 rounded-full border-2 border-transparent border-b-pink-500 border-l-purple-500 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1s' }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg">✦</span>
        </div>
      </div>

      {/* Animated message */}
      <p className="text-sm font-mono text-gray-400 text-center px-4 transition-all duration-500" key={index}>
        {message || MESSAGES[index]}
      </p>

      {/* Dots */}
      <div className="flex gap-1.5">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-purple-500/50"
            style={{ animation: `pulse 1.5s ease-in-out ${i * 0.3}s infinite` }}
          />
        ))}
      </div>
    </div>
  )
}
