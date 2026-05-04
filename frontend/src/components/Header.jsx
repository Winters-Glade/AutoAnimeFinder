export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-cyber-border bg-cyber-black/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center">
              <span className="text-black text-sm font-bold">AS</span>
            </div>
            <span className="font-display text-lg font-semibold text-white">
              Anime Soul Whisper
            </span>
          </div>

          {/* Status */}
          <nav className="flex items-center gap-6">
            <span className="text-xs text-gray-500 font-mono hidden sm:block">
              <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse mr-2" />
              Neural Engine Active
            </span>
          </nav>
        </div>
      </div>
    </header>
  )
}
