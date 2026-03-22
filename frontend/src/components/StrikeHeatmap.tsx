import type { StrikeMapEntry } from '../hooks/useWebSocket'

function barColor(heat: number, isCE: boolean): string {
  if (heat >= 4) return isCE ? 'bg-emerald-400' : 'bg-red-400'
  if (heat >= 2) return isCE ? 'bg-emerald-600' : 'bg-red-600'
  if (heat >= 1) return isCE ? 'bg-emerald-800/60' : 'bg-red-800/60'
  return 'bg-tb-border/50'
}

export default function StrikeHeatmap({ strikeMap, atm }: { strikeMap: StrikeMapEntry[]; atm: number }) {
  if (!strikeMap.length) {
    const now = new Date()
    const day = now.getDay() // 0=Sun, 6=Sat
    const hour = now.getHours()
    const isWeekend = day === 0 || day === 6
    const isAfterHours = !isWeekend && (hour < 9 || hour >= 16)
    const isMarketClosed = isWeekend || isAfterHours

    return (
      <div className="h-full flex flex-col items-center justify-center text-center px-6">
        {isMarketClosed ? (
          <>
            <div className="text-3xl mb-3">{isWeekend ? '📅' : '🌙'}</div>
            <p className="text-tb-muted text-sm font-semibold mb-1">
              {isWeekend ? 'Market Closed — Weekend' : 'Market Closed — After Hours'}
            </p>
            <p className="text-tb-muted/50 text-[10px] leading-relaxed">
              {isWeekend
                ? 'Markets reopen Monday 9:15 AM IST. Last trading day data will load from Kite API after the first data cycle.'
                : 'Market hours: 9:15 AM — 3:30 PM IST. Pre-market data will appear closer to open.'}
            </p>
            <p className="text-tb-muted/30 text-[9px] mt-3">Detectors show last available data from Kite API</p>
          </>
        ) : (
          <>
            <div className="w-8 h-8 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mb-3" />
            <p className="text-tb-muted text-sm">Loading option chain from Kite API...</p>
            <p className="text-tb-muted/40 text-[9px] mt-1">First load takes ~10 seconds</p>
          </>
        )}
      </div>
    )
  }

  const ceTotal = strikeMap.reduce((s, e) => s + e.ce_heat, 0)
  const peTotal = strikeMap.reduce((s, e) => s + e.pe_heat, 0)
  const dir = ceTotal > peTotal ? 'BULLISH' : peTotal > ceTotal ? 'BEARISH' : 'NEUTRAL'

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="text-[11px] font-bold text-neon-cyan uppercase tracking-widest">Strike Heatmap</h2>
        <span className="text-[10px] font-mono text-tb-muted">CE vs PE Signals</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-px">
        {strikeMap.map((e) => (
          <div key={e.strike} className={`flex items-center gap-1.5 px-2 py-[3px] rounded-md text-[11px] font-mono transition-colors ${
            e.is_atm ? 'bg-neon-cyan/8 ring-1 ring-neon-cyan/20' : 'hover:bg-tb-surface/50'
          }`}>
            {/* CE bar */}
            <div className="w-24 flex justify-end"><div className={`h-2.5 rounded-sm transition-all duration-500 ${barColor(e.ce_heat, true)}`} style={{ width: `${Math.min(100, e.ce_heat * 18)}%`, minWidth: e.ce_heat > 0 ? '4px' : 0 }} /></div>
            {/* Strike */}
            <span className={`w-12 text-center text-[11px] ${e.is_atm ? 'text-neon-cyan font-bold' : 'text-tb-text/80'}`}>{e.strike}</span>
            {/* PE bar */}
            <div className="w-24"><div className={`h-2.5 rounded-sm transition-all duration-500 ${barColor(e.pe_heat, false)}`} style={{ width: `${Math.min(100, e.pe_heat * 18)}%`, minWidth: e.pe_heat > 0 ? '4px' : 0 }} /></div>
            {/* Label */}
            <span className={`text-[9px] w-10 ${
              e.label === 'HOT' ? 'text-neon-red font-bold blink' :
              e.label === 'loading' ? 'text-neon-orange font-semibold' :
              e.label === 'mild' ? 'text-neon-yellow' : 'text-tb-muted/40'
            }`}>{e.is_atm ? 'ATM' : e.label !== 'neutral' ? e.label.toUpperCase() : ''}</span>
          </div>
        ))}
      </div>
      <div className={`mt-2 text-center text-[11px] font-bold py-2 rounded-xl ${
        dir === 'BULLISH' ? 'text-neon-green bg-emerald-950/20 border border-emerald-800/20' :
        dir === 'BEARISH' ? 'text-neon-red bg-red-950/20 border border-red-800/20' : 'text-tb-muted bg-tb-surface'
      }`}>
        {dir === 'BULLISH' ? '▲' : dir === 'BEARISH' ? '▼' : '●'} {dir} — CE:{ceTotal} vs PE:{peTotal}
      </div>
    </div>
  )
}
