import NeuralLoader from './NeuralLoader'

function Stat({ label, value }) {
  return (
    <div className="bg-cyber-dark/50 rounded-lg p-3 text-center border border-cyber-border">
      <div className="text-xl font-bold text-white font-display">{value ?? '—'}</div>
      <div className="text-xs text-cyber-muted font-mono mt-0.5">{label}</div>
    </div>
  )
}

export default function TasteProfile({ profile, loading }) {
  if (loading) return <NeuralLoader />
  if (!profile) {
    return (
      <div className="cyber-card p-5 text-center">
        <div className="text-3xl mb-3">🧬</div>
        <p className="text-sm text-cyber-muted font-mono">
          Import your anime list to unlock your Anime DNA
        </p>
      </div>
    )
  }

  return (
    <div className="cyber-card p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="neon-text text-lg font-bold font-display">🧬 ANIME DNA DECODED</h3>
        <span className="badge-purple text-[10px] uppercase">{profile.source || 'anilist'}</span>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Completed" value={`${profile.completedAnime ?? 0}/${profile.totalAnime ?? profile.total_anime}`} />
        <Stat label="Avg Score" value={((profile.ratingPatterns ?? profile.ratings)?.averageScore ?? profile.average_score)?.toFixed(1)} />
        <Stat label="Binge Level" value={Math.round((profile.bingePotential?.bingeScore ?? profile.binge_potential ?? 0) * 100) + '%'} />
        <Stat label="Critic Type" value={(profile.ratingPatterns?.harshCritic ?? profile.is_harsh_critic) ? '😈 Harsh' : '😇 Generous'} />
      </div>

      {/* Top Genres */}
      {(profile.topGenres ?? profile.top_genres)?.length > 0 && (
        <div>
          <h4 className="text-xs font-mono text-neon-blue uppercase tracking-wider mb-3">Top Genres</h4>
          <div className="space-y-2">
            {(profile.topGenres ?? profile.top_genres).slice(0, 5).map((g) => {
              const name = g.genre
              const weight = g.score
              return (
                <div key={name} className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-400 w-24 text-right truncate">{name}</span>
                  <div className="flex-1 h-2.5 bg-cyber-dark rounded-full overflow-hidden border border-cyber-border">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${Math.min(weight, 100)}%`,
                        background: 'linear-gradient(90deg, #00d4ff, #a855f7, #ec4899)',
                        boxShadow: '0 0 8px rgba(168,85,247,0.3)',
                      }}
                    />
                  </div>
                  <span className="text-xs font-mono text-cyber-muted w-8 text-right">{Math.round(weight)}%</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Top Tags */}
      {(profile.topTags ?? profile.top_tags)?.length > 0 && (
        <div>
          <h4 className="text-xs font-mono text-neon-purple uppercase tracking-wider mb-3">Top Tags</h4>
          <div className="flex flex-wrap gap-1.5">
            {(profile.topTags ?? profile.top_tags).slice(0, 8).map((t) => {
              const name = t.tag
              return (
                <span
                  key={name}
                  className="px-2 py-1 text-[10px] font-mono rounded-full bg-neon-purple/10 text-neon-purple border border-neon-purple/20"
                >
                  #{name}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* Top Studios */}
      {(profile.topStudios ?? profile.top_studios)?.length > 0 && (
        <div>
          <h4 className="text-xs font-mono text-neon-pink uppercase tracking-wider mb-2">Top Studios</h4>
          <div className="flex flex-wrap gap-1.5">
            {(profile.topStudios ?? profile.top_studios).slice(0, 5).map((s) => {
              const name = s.studio
              return (
                <span key={name} className="badge-blue text-[10px]">{name}</span>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
