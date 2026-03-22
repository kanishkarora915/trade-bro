export default function TopBar({ spot, atm, connected, latency, userName, onLogout, indiaVix, vixEnabled, onToggleVix }: {
  spot: number; atm: number; connected: boolean; latency: number; userName: string; onLogout: () => void
  indiaVix?: number; vixEnabled?: boolean; onToggleVix?: () => void
}) {
  const speedColor = latency < 100 ? 'text-neon-green' : latency < 300 ? 'text-neon-yellow' : 'text-neon-red'
  const speedLabel = latency < 100 ? 'Fast' : latency < 300 ? 'Medium' : 'Slow'

  // VIX color: <14 green (complacent), 14-20 yellow (normal), >20 red (fear)
  const vixColor = (indiaVix || 0) > 20 ? 'text-neon-red' : (indiaVix || 0) > 14 ? 'text-neon-yellow' : 'text-neon-green'
  const vixLabel = (indiaVix || 0) > 25 ? 'FEAR' : (indiaVix || 0) > 20 ? 'HIGH' : (indiaVix || 0) > 14 ? 'NORMAL' : 'LOW'

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

      {/* Center — Market Data + VIX */}
      <div className="flex items-center gap-5 font-mono text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-tb-muted text-[10px]">NIFTY</span>
          <span className="text-neon-green font-bold text-sm">{spot ? spot.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}</span>
        </div>
        <div className="hidden md:flex items-center gap-1.5">
          <span className="text-tb-muted text-[10px]">ATM</span>
          <span className="text-tb-text font-semibold">{atm || '—'}</span>
        </div>

        {/* India VIX with ON/OFF toggle */}
        {indiaVix !== undefined && indiaVix > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-tb-muted text-[10px]">VIX</span>
            <span className={`font-bold text-sm ${vixColor}`}>{indiaVix.toFixed(2)}</span>
            <span className={`text-[8px] px-1 py-0.5 rounded font-bold ${
              vixLabel === 'FEAR' ? 'bg-red-950/40 text-neon-red' :
              vixLabel === 'HIGH' ? 'bg-orange-950/40 text-neon-orange' :
              vixLabel === 'NORMAL' ? 'bg-yellow-950/40 text-neon-yellow' :
              'bg-emerald-950/40 text-neon-green'
            }`}>{vixLabel}</span>
            {onToggleVix && (
              <button
                onClick={onToggleVix}
                className={`text-[8px] font-bold px-1.5 py-0.5 rounded border transition-all ${
                  vixEnabled
                    ? 'bg-neon-cyan/15 border-neon-cyan/40 text-neon-cyan hover:bg-neon-cyan/25'
                    : 'bg-tb-card border-tb-border text-tb-muted hover:text-tb-text'
                }`}
                title={vixEnabled ? 'VIX is boosting detector scores when >20. Click to disable.' : 'VIX integration disabled. Click to enable.'}
              >
                {vixEnabled ? 'ON' : 'OFF'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Right — Status */}
      <div className="flex items-center gap-4">
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
