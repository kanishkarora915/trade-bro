import type { StrikeMapEntry } from '../hooks/useWebSocket'

function barColor(heat: number, isCE: boolean): string {
  if (heat >= 4) return isCE ? 'bg-emerald-400' : 'bg-red-400'
  if (heat >= 2) return isCE ? 'bg-emerald-600' : 'bg-red-600'
  if (heat >= 1) return isCE ? 'bg-emerald-800/60' : 'bg-red-800/60'
  return 'bg-tb-border/50'
}

export default function StrikeHeatmap({ strikeMap, atm }: { strikeMap: StrikeMapEntry[]; atm: number }) {
  if (!strikeMap.length) return (
    <div className="h-full flex items-center justify-center text-tb-muted text-sm">Connecting to Kite API...</div>
  )

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
