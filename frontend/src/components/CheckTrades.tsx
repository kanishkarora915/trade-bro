import type { TradeState } from '../hooks/useWebSocket'

interface Props { state: TradeState }

interface Setup {
  strike: string; side: string; direction: string; index: string
  ltp: number; entry: number; target: number; sl: number
  score: number; status: string; reason: string
  reason_details: string[]; timeframes: Record<string, string>
  time: string; timestamp: string
}

const DIR_CLR: Record<string, string> = {
  BULL: 'text-green-400', BEAR: 'text-red-400', WARNING: 'text-yellow-400',
}
const DIR_BG: Record<string, string> = {
  BULL: 'border-green-700/40 bg-emerald-950/20',
  BEAR: 'border-red-700/40 bg-red-950/20',
  WARNING: 'border-yellow-700/40 bg-yellow-950/20',
}
const STATUS_CLR: Record<string, string> = {
  ACTIVE: 'bg-green-500/20 text-green-400 border-green-500/40',
  WATCHING: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  WARNING: 'bg-red-500/20 text-red-400 border-red-500/40',
  EXPIRED: 'bg-gray-500/20 text-gray-400 border-gray-500/40',
}
const TF_CLR: Record<string, string> = {
  BULLISH: 'text-green-400', BEARISH: 'text-red-400', SIDEWAYS: 'text-gray-400', UNKNOWN: 'text-gray-600',
}

export default function CheckTrades({ state }: Props) {
  const { spot, atm, active_index } = state
  const setups: Setup[] = (state as any).check_trades || []
  const zone = (state as any).zone_analysis || {}
  const tf = (state as any).timeframe_data || {}

  const activeSetups = setups.filter(s => s.status === 'ACTIVE')
  const watchingSetups = setups.filter(s => s.status === 'WATCHING')
  const warnings = setups.filter(s => s.status === 'WARNING')

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header summary bar */}
      <div className="shrink-0 bg-gray-900/60 border-b border-gray-700 px-4 py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-sm font-extrabold text-orange-400 uppercase tracking-widest">Check Trades</h1>
            <span className="text-gray-500 text-[11px]">MTF + OI Explosion Detection</span>
          </div>
          <div className="flex items-center gap-5 text-[11px] font-mono">
            <span className="text-gray-400">SPOT <span className="text-white font-bold text-sm">{spot.toLocaleString('en-IN')}</span></span>
            <span className="text-gray-400">ATM <span className="text-cyan-400 font-bold">{atm}</span></span>
            <span className="text-gray-400">IDX <span className="text-purple-400 font-bold">{active_index}</span></span>
            {zone.support_zone && <span className="text-green-400 font-bold">S: {zone.support_zone}</span>}
            {zone.resistance_zone && <span className="text-red-400 font-bold">R: {zone.resistance_zone}</span>}
          </div>
        </div>
        {/* Timeframe alignment strip */}
        <div className="flex items-center gap-3 mt-1.5">
          <span className="text-gray-500 text-[10px] font-bold">TIMEFRAMES:</span>
          {Object.entries(tf).map(([key, data]: [string, any]) => (
            <span key={key} className={`text-[10px] font-bold px-2 py-0.5 rounded border border-gray-700/50 bg-gray-800/30 ${TF_CLR[data?.trend || 'UNKNOWN']}`}>
              {key.toUpperCase()} {data?.trend === 'BULLISH' ? '▲' : data?.trend === 'BEARISH' ? '▼' : '—'}
            </span>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* No setups */}
        {setups.length === 0 && (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg font-bold mb-2">Scanning for setups...</p>
            <p className="text-gray-600 text-sm">Check Trades engine is analyzing MTF + OI data across all timeframes.</p>
            <p className="text-gray-600 text-sm mt-1">Setups will appear when pre-explosion patterns are detected.</p>
          </div>
        )}

        {/* ACTIVE TRADES — big prominent cards */}
        {activeSetups.length > 0 && (
          <div>
            <h2 className="text-[12px] font-extrabold text-green-400 uppercase tracking-widest mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" /> Active Trade Setups ({activeSetups.length})
            </h2>
            <div className="space-y-3">
              {activeSetups.map((s, i) => (
                <TradeCard key={i} setup={s} />
              ))}
            </div>
          </div>
        )}

        {/* WATCHING — smaller cards */}
        {watchingSetups.length > 0 && (
          <div>
            <h2 className="text-[12px] font-extrabold text-yellow-400 uppercase tracking-widest mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-400" /> Watching ({watchingSetups.length})
            </h2>
            <div className="space-y-2">
              {watchingSetups.map((s, i) => (
                <TradeCard key={i} setup={s} compact />
              ))}
            </div>
          </div>
        )}

        {/* WARNINGS — trap zones */}
        {warnings.length > 0 && (
          <div>
            <h2 className="text-[12px] font-extrabold text-red-400 uppercase tracking-widest mb-3">
              ⚠️ Warnings & Trap Zones
            </h2>
            <div className="space-y-2">
              {warnings.map((s, i) => (
                <div key={i} className="bg-yellow-950/15 border border-yellow-700/30 rounded-xl p-3">
                  <p className="text-yellow-400 font-bold text-[13px]">{s.reason}</p>
                  <div className="mt-1.5 space-y-0.5">
                    {s.reason_details.map((r, j) => (
                      <p key={j} className="text-gray-400 text-[11px]">• {r}</p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


function TradeCard({ setup: s, compact }: { setup: Setup; compact?: boolean }) {
  const isBull = s.direction === 'BULL'
  const pnlPct = s.entry > 0 ? ((s.ltp - s.entry) / s.entry * 100) : 0

  return (
    <div className={`rounded-xl border ${DIR_BG[s.direction] || DIR_BG.WARNING} p-4`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className={`text-2xl font-black ${DIR_CLR[s.direction]}`}>
            {isBull ? '▲' : s.direction === 'BEAR' ? '▼' : '⚠️'} {s.direction === 'WARNING' ? '' : (isBull ? 'BUY' : 'SELL')} {s.strike}
          </span>
          <span className={`text-[10px] px-2.5 py-1 rounded-lg font-extrabold border ${STATUS_CLR[s.status] || STATUS_CLR.EXPIRED}`}>
            {s.status}
          </span>
          <span className="text-gray-500 text-[11px] font-mono">{s.index} • {s.time}</span>
        </div>
        <div className="text-right">
          <span className={`text-2xl font-black font-mono ${s.score >= 70 ? 'text-green-400' : s.score >= 50 ? 'text-yellow-400' : 'text-gray-400'}`}>
            {s.score.toFixed(0)}
          </span>
          <span className="text-gray-500 text-[10px] block">SCORE</span>
        </div>
      </div>

      {/* Trade details grid */}
      {s.entry > 0 && (
        <div className="grid grid-cols-6 gap-2 mb-3">
          {[
            { label: 'LTP', val: `₹${s.ltp}`, clr: 'text-white' },
            { label: 'ENTRY', val: `₹${s.entry}`, clr: 'text-cyan-400' },
            { label: 'TARGET', val: `₹${s.target}`, clr: 'text-green-400' },
            { label: 'STOP LOSS', val: `₹${s.sl}`, clr: 'text-red-400' },
            { label: 'P&L', val: `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%`, clr: pnlPct >= 0 ? 'text-green-400' : 'text-red-400' },
            { label: 'STATUS', val: s.status, clr: s.status === 'ACTIVE' ? 'text-green-400' : 'text-yellow-400' },
          ].map(x => (
            <div key={x.label} className="bg-black/20 rounded-lg p-2.5 text-center">
              <span className="text-gray-500 text-[9px] block font-bold uppercase">{x.label}</span>
              <span className={`${x.clr} font-extrabold text-[15px]`}>{x.val}</span>
            </div>
          ))}
        </div>
      )}

      {/* Reason box */}
      <div className="bg-black/15 rounded-lg p-3 border border-gray-700/30">
        <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">WHY THIS TRADE?</p>
        <p className={`text-[13px] font-bold mb-2 ${DIR_CLR[s.direction]}`}>{s.reason}</p>
        {!compact && s.reason_details.map((r, i) => (
          <p key={i} className="text-gray-300 text-[11px] leading-relaxed">• {r}</p>
        ))}
      </div>

      {/* Timeframe alignment */}
      {!compact && s.timeframes && Object.keys(s.timeframes).length > 0 && (
        <div className="mt-2.5 flex items-center gap-2">
          <span className="text-gray-500 text-[10px] font-bold">TF ALIGNMENT:</span>
          {Object.entries(s.timeframes).map(([tf, trend]) => (
            <span key={tf} className={`text-[9px] font-bold px-1.5 py-0.5 rounded bg-gray-800/50 ${TF_CLR[trend as string] || 'text-gray-600'}`}>
              {tf} {trend === 'BULLISH' ? '▲' : trend === 'BEARISH' ? '▼' : '—'}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
