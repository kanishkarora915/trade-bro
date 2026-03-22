export default function TopBar({ spot, atm, connected, latency, userName, onLogout }: {
  spot: number; atm: number; connected: boolean; latency: number; userName: string; onLogout: () => void
}) {
  const speedColor = latency < 100 ? 'text-neon-green' : latency < 300 ? 'text-neon-yellow' : 'text-neon-red'
  const speedLabel = latency < 100 ? 'Fast' : latency < 300 ? 'Medium' : 'Slow'

  return (
    <header className="shrink-0 flex items-center justify-between px-5 py-2.5 bg-tb-card/80 backdrop-blur-sm border-b border-tb-border">
      {/* Left — Brand */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 bg-gradient-to-br from-neon-cyan to-neon-blue rounded-lg flex items-center justify-center text-[10px] font-black text-tb-bg">TB</div>
        <div>
          <span className="text-sm font-extrabold tracking-tight text-tb-text">TRADE BRO</span>
          <span className="text-[9px] text-tb-muted ml-2 hidden sm:inline">OPTIONS BOOM DETECTOR</span>
        </div>
      </div>

      {/* Center — Market Data */}
      <div className="flex items-center gap-6 font-mono text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-tb-muted text-[10px]">NIFTY</span>
          <span className="text-neon-green font-bold text-sm">{spot ? spot.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}</span>
        </div>
        <div className="hidden md:flex items-center gap-1.5">
          <span className="text-tb-muted text-[10px]">ATM</span>
          <span className="text-tb-text font-semibold">{atm || '—'}</span>
        </div>
      </div>

      {/* Right — Status */}
      <div className="flex items-center gap-4">
        {/* Network Status */}
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <div className={`flex items-center gap-1.5 ${connected ? 'text-neon-green' : 'text-neon-red'}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-neon-green' : 'bg-neon-red animate-pulse-dot'}`} />
            {connected ? 'LIVE' : 'OFFLINE'}
          </div>
          {connected && (
            <div className={`flex items-center gap-1 ${speedColor}`}>
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M3.5 13A1.5 1.5 0 005 14.5V17a1 1 0 002 0v-2.5a3.5 3.5 0 00-7 0V17a1 1 0 002 0v-2.5A1.5 1.5 0 003.5 13zM9 9a1 1 0 012 0v8a1 1 0 01-2 0V9zm4-2a1 1 0 012 0v10a1 1 0 01-2 0V7zm4-4a1 1 0 012 0v14a1 1 0 01-2 0V3z"/></svg>
              <span>{latency}ms</span>
              <span className="text-tb-muted">({speedLabel})</span>
            </div>
          )}
        </div>

        {/* User */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-tb-muted hidden lg:block">{userName}</span>
          <button onClick={onLogout} className="text-[10px] text-tb-muted hover:text-neon-red transition-colors px-2 py-1 rounded border border-tb-border hover:border-red-900/50">
            Logout
          </button>
        </div>
      </div>
    </header>
  )
}
