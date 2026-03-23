import { useState } from 'react'
import type { TradeState, DetectorResult } from '../hooks/useWebSocket'

interface Props { state: TradeState; onBack: () => void }

const TYPE_CLR: Record<string, string> = { BUY: 'text-neon-green', SELL: 'text-neon-red', NEUTRAL: 'text-gray-400' }
const TYPE_BG: Record<string, string> = { BUY: 'bg-emerald-950/25 border-emerald-700/30', SELL: 'bg-red-950/25 border-red-700/30', NEUTRAL: 'bg-tb-surface/30 border-tb-border' }
const STR_CLR: Record<string, string> = { EXTREME: 'bg-red-500/25 text-red-400 border border-red-500/40', AGGRESSIVE: 'bg-neon-red/20 text-neon-red', STRONG: 'bg-neon-green/20 text-neon-green', MILD: 'bg-neon-yellow/20 text-neon-yellow' }

/** Parse ISO or time string to HH:MM:SS in IST */
function fmtTime(t: string): string {
  if (!t) return '--:--:--'
  try {
    // If it's just HH:MM:SS already
    if (/^\d{2}:\d{2}:\d{2}$/.test(t)) return t
    // Parse ISO — add IST offset if no timezone specified
    const d = new Date(t.includes('+') || t.includes('Z') ? t : t + '+05:30')
    const h = d.getHours().toString().padStart(2, '0')
    const m = d.getMinutes().toString().padStart(2, '0')
    const s = d.getSeconds().toString().padStart(2, '0')
    return `${h}:${m}:${s}`
  } catch { return '--:--:--' }
}

function fmtTimeShort(t: string): string {
  const full = fmtTime(t)
  return full.slice(0, 5) // HH:MM
}

export default function FlowDashboard({ state, onBack }: Props) {
  const { brain, confluence, flow_tape: tape, signal_history, detectors, ai_analysis, spot, atm, india_vix, fii_dii } = state
  const [filter, setFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL')
  const [expandedDet, setExpandedDet] = useState<string | null>(null)
  const [showAI, setShowAI] = useState(false)

  const sig = brain.active && brain.primary ? brain : null
  const filtered = [...(tape || [])].filter(f => filter === 'ALL' || f.type === filter).reverse()
  const detList = Object.values(detectors || {}).sort((a, b) => b.score - a.score)
  const history = signal_history ? [...signal_history].reverse().slice(0, 20) : []

  const vixLabel = india_vix ? (india_vix > 20 ? 'FEAR' : india_vix > 14 ? 'CAUTION' : 'GREED') : null
  const vixClr = india_vix ? (india_vix > 20 ? 'text-red-400' : india_vix > 14 ? 'text-yellow-400' : 'text-green-400') : ''
  const dirClr = confluence.direction === 'BULLISH' ? 'text-green-400' : confluence.direction === 'BEARISH' ? 'text-red-400' : 'text-gray-300'

  return (
    <div className="h-screen flex flex-col bg-tb-bg overflow-hidden">
      {/* SECTION 1: LIVE TRADE SIGNAL — top banner */}
      <div className={`shrink-0 border-b ${sig ? 'border-green-500/40 bg-emerald-950/15' : 'border-tb-border bg-tb-card/30'}`}>
        <div className="flex items-center justify-between px-5 py-2">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="text-cyan-400 hover:text-cyan-300 text-sm font-bold">← Main</button>
            <span className="text-gray-600">|</span>
            <h1 className="text-sm font-extrabold tracking-widest text-purple-400 uppercase">Flow Dashboard</h1>
          </div>
          <div className="flex items-center gap-5 text-xs font-mono">
            <span className="text-gray-400">SPOT <span className="text-white font-bold text-sm">{spot.toLocaleString('en-IN')}</span></span>
            <span className="text-gray-400">ATM <span className="text-cyan-400 font-bold text-sm">{atm}</span></span>
          </div>
        </div>
        <div className="px-5 pb-2.5">
          {sig && sig.primary ? (
            <div className="flex items-center gap-6 flex-wrap">
              <div className="flex items-center gap-3">
                <span className={`text-2xl font-black ${sig.direction === 'BULLISH' ? 'text-green-400' : 'text-red-400'}`}>
                  {sig.primary.action} {sig.primary.strike}
                </span>
                {sig.strength && <span className={`text-[10px] px-2.5 py-1 rounded-lg font-extrabold ${STR_CLR[sig.strength] || 'bg-tb-surface text-gray-400'}`}>{sig.strength}</span>}
              </div>
              <div className="flex items-center gap-5 text-xs font-mono">
                <span className="text-gray-300">CMP <span className="text-white font-bold">{sig.primary.cmp}</span></span>
                <span className="text-gray-300">T1 <span className="text-green-400 font-bold">{sig.primary.target1}</span></span>
                <span className="text-gray-300">T2 <span className="text-green-400 font-bold">{sig.primary.target2}</span></span>
                <span className="text-gray-300">SL <span className="text-red-400 font-bold">{sig.primary.stop_loss}</span></span>
                <span className="text-gray-300">TL <span className="text-yellow-400">{sig.primary.time_limit}</span></span>
              </div>
              {sig.secondary && (
                <span className="text-xs font-mono text-orange-400 font-bold">ALT: {sig.secondary.action} {sig.secondary.strike} @ {sig.secondary.cmp}</span>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-xs font-mono">Monitoring... No active signal — Score: {confluence.score.toFixed(0)}/100</p>
          )}
        </div>
      </div>

      {/* MAIN 3-COL GRID */}
      <div className="flex-1 grid grid-cols-[300px_1fr_340px] gap-[1px] bg-tb-border overflow-hidden">

        {/* SECTION 2: SIGNAL HISTORY — left column (card layout) */}
        <div className="bg-tb-bg p-3 flex flex-col overflow-hidden">
          <h2 className="text-xs font-extrabold text-green-400 uppercase tracking-widest mb-2 shrink-0">📡 Signal History ({history.length})</h2>
          <div className="flex-1 overflow-y-auto space-y-2">
            {history.length === 0 && <p className="text-gray-500 text-center py-8 text-sm">No signals recorded yet</p>}
            {history.map((s, i) => {
              const bull = s.direction === 'BULLISH'
              const pnl = s.spot_at_signal && spot ? ((spot - s.spot_at_signal) * (bull ? 1 : -1)).toFixed(1) : null
              return (
                <div key={i} className={`rounded-xl p-3 border ${bull ? 'border-green-700/40 bg-emerald-950/20' : 'border-red-700/40 bg-red-950/20'}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-black ${bull ? 'text-green-400' : 'text-red-400'}`}>{bull ? '▲' : '▼'}</span>
                      <span className="text-white font-bold text-sm">{s.primary?.strike || '—'}</span>
                      <span className="text-gray-400 text-[10px] font-mono">{(s.index || '').slice(0, 3)}</span>
                    </div>
                    <span className="text-gray-400 text-[11px] font-mono">{fmtTimeShort(s.recorded_at || '')}</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-[11px] font-mono">
                    <div>
                      <span className="text-gray-500 text-[9px] block">ENTRY</span>
                      <span className="text-white font-bold">{s.primary?.cmp || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-[9px] block">TARGET</span>
                      <span className="text-green-400 font-bold">{s.primary?.target1 || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-[9px] block">SL</span>
                      <span className="text-red-400 font-bold">{s.primary?.stop_loss || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-[9px] block">SPOT</span>
                      <span className="text-gray-300">{s.spot_at_signal?.toLocaleString('en-IN') || '—'}</span>
                    </div>
                  </div>
                  {pnl && (
                    <div className={`mt-1.5 pt-1.5 border-t border-gray-800 text-[10px] font-mono ${Number(pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      NIFTY Move: {Number(pnl) >= 0 ? '+' : ''}{pnl} pts since signal
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* SECTION 3: DETAILED FLOW TAPE — center, scrollable */}
        <div className="bg-tb-bg p-3 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-2 shrink-0">
            <h2 className="text-xs font-extrabold text-purple-400 uppercase tracking-widest">Options Flow Tape</h2>
            <div className="flex items-center gap-1.5">
              {(['ALL', 'BUY', 'SELL'] as const).map(f => (
                <button key={f} onClick={() => setFilter(f)} className={`text-[10px] px-3 py-1 rounded-lg font-bold transition-all ${filter === f ? (f === 'BUY' ? 'bg-emerald-900/60 text-green-400 border border-green-700/40' : f === 'SELL' ? 'bg-red-900/60 text-red-400 border border-red-700/40' : 'bg-tb-surface text-cyan-400 border border-cyan-700/40') : 'text-gray-500 hover:text-gray-300 border border-transparent'}`}>{f}</button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3 px-2 py-2 text-[10px] text-gray-400 uppercase font-mono font-bold border-b border-gray-700 shrink-0">
            <span className="w-16">Time</span><span className="w-8">Idx</span><span className="w-24">Strike</span>
            <span className="w-16 text-right">Price</span><span className="w-20 text-right">Volume</span>
            <span className="w-20 text-right">OI</span><span className="w-20 text-right">Value</span><span className="w-16">Type</span>
          </div>
          <div className="flex-1 overflow-y-auto font-mono text-[11px]">
            {filtered.length === 0 && <p className="text-gray-500 text-center py-10 text-sm">No flow data yet</p>}
            {filtered.map((f, i) => {
              const val = f.price * f.volume * 25
              return (
                <div key={i} className={`flex items-center gap-3 px-2 py-1.5 border-l-[3px] ${TYPE_BG[f.type]} hover:brightness-125 transition-all`}>
                  <span className="text-gray-300 w-16 font-semibold">{fmtTime(f.time)}</span>
                  <span className="text-gray-400 w-8">{(f.index || '').slice(0, 3)}</span>
                  <span className="text-white font-bold w-24">{f.strike}</span>
                  <span className="text-white w-16 text-right font-bold">₹{f.price.toFixed(1)}</span>
                  <span className={`w-20 text-right font-bold ${f.volume > 5000 ? 'text-yellow-400' : 'text-gray-200'}`}>{f.volume.toLocaleString()}</span>
                  <span className="text-gray-300 w-20 text-right">{f.oi.toLocaleString()}</span>
                  <span className="text-gray-200 w-20 text-right font-semibold">{val > 1e7 ? `${(val / 1e7).toFixed(1)}Cr` : val > 1e5 ? `${(val / 1e5).toFixed(1)}L` : val.toLocaleString()}</span>
                  <span className={`font-extrabold w-16 text-[12px] ${TYPE_CLR[f.type]}`}>{f.type === 'BUY' ? '▲ BUY' : f.type === 'SELL' ? '▼ SELL' : '— —'}</span>
                </div>
              )
            })}
          </div>
          <div className="shrink-0 flex items-center justify-between mt-1.5 pt-1.5 border-t border-gray-700 text-[10px] font-mono">
            <span className="text-gray-400 font-semibold">{filtered.length} entries</span>
            <div className="flex gap-4">
              <span className="text-green-400 font-bold">BUY {(tape || []).filter(t => t.type === 'BUY').length}</span>
              <span className="text-red-400 font-bold">SELL {(tape || []).filter(t => t.type === 'SELL').length}</span>
            </div>
          </div>
        </div>

        {/* SECTION 4: DETECTOR BREAKDOWN — right column */}
        <div className="bg-tb-bg p-3 flex flex-col overflow-hidden">
          <h2 className="text-xs font-extrabold text-cyan-400 uppercase tracking-widest mb-2 shrink-0">Detectors ({detList.length})</h2>
          <div className="flex-1 overflow-y-auto space-y-1.5">
            {detList.map((d: DetectorResult) => (
              <div key={d.id} className={`border rounded-xl p-2.5 cursor-pointer transition-all ${
                d.status === 'CRITICAL' ? 'border-green-500/50 bg-emerald-950/20' :
                d.status === 'ALERT' ? 'border-green-600/30 bg-emerald-950/10' :
                d.status === 'WATCH' ? 'border-yellow-600/30 bg-yellow-950/10' :
                'border-gray-700/40 hover:bg-gray-900/30'
              }`} onClick={() => setExpandedDet(expandedDet === d.id ? null : d.id)}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[12px] font-bold ${d.score > 0 ? 'text-white' : 'text-gray-500'}`}>{d.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[12px] font-mono font-extrabold ${d.score >= 70 ? 'text-green-400' : d.score >= 30 ? 'text-yellow-400' : 'text-gray-600'}`}>{d.score}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-md font-extrabold ${
                      d.status === 'CRITICAL' ? 'bg-green-500/25 text-green-400' :
                      d.status === 'ALERT' ? 'bg-green-600/20 text-green-400' :
                      d.status === 'WATCH' ? 'bg-yellow-600/20 text-yellow-400' :
                      'bg-gray-800/50 text-gray-500'
                    }`}>{d.status}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${
                      d.status === 'CRITICAL' ? 'bg-green-500' :
                      d.status === 'ALERT' ? 'bg-green-600' :
                      d.status === 'WATCH' ? 'bg-yellow-500' :
                      'bg-gray-700'
                    }`} style={{ width: `${Math.min(d.score, 100)}%` }} />
                  </div>
                </div>
                <p className={`text-[11px] ${d.score > 0 ? 'text-gray-300' : 'text-gray-600'}`}>{d.metric}</p>
                {expandedDet === d.id && d.alerts && d.alerts.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-700/50 space-y-1">
                    {d.alerts.slice(0, 5).map((a: any, i: number) => (
                      <p key={i} className="text-[10px] text-yellow-400 font-mono">{typeof a === 'string' ? a : JSON.stringify(a)}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SECTION 5: MARKET CONTEXT — bottom bar */}
      <div className="shrink-0 flex items-center justify-between px-5 py-2 bg-gray-900/60 border-t border-gray-700 text-[11px] font-mono">
        <div className="flex items-center gap-5">
          {india_vix != null && (
            <span className="text-gray-300">VIX <span className={`font-bold ${vixClr}`}>{india_vix.toFixed(2)}</span> <span className={`text-[9px] font-bold ${vixClr}`}>{vixLabel}</span></span>
          )}
          {fii_dii && (
            <>
              <span className="text-gray-300">FII <span className={`font-bold ${(fii_dii.fii_net_cr || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{(fii_dii.fii_net_cr || 0) >= 0 ? '+' : ''}{fii_dii.fii_net_cr?.toFixed(0)}Cr</span></span>
              <span className="text-gray-300">DII <span className={`font-bold ${(fii_dii.dii_net_cr || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{(fii_dii.dii_net_cr || 0) >= 0 ? '+' : ''}{fii_dii.dii_net_cr?.toFixed(0)}Cr</span></span>
            </>
          )}
        </div>
        <div className="flex items-center gap-5">
          <span className={`font-extrabold ${dirClr}`}>{confluence.direction} {confluence.score.toFixed(0)}/100</span>
          <span className="text-gray-300">IDX <span className="text-cyan-400 font-bold">{state.active_index || 'NIFTY'}</span></span>
          <span className="text-gray-300">SPOT <span className="text-white font-bold">{spot.toLocaleString('en-IN')}</span></span>
        </div>
        <button onClick={() => setShowAI(!showAI)} className={`text-[10px] px-3 py-1 rounded-lg font-bold transition-all ${showAI ? 'bg-purple-900/40 text-purple-400 border border-purple-600/40' : 'text-gray-400 hover:text-purple-400 border border-gray-700'}`}>
          {showAI ? 'Hide AI' : '🤖 AI Analysis'}
        </button>
      </div>

      {/* SECTION 6: AI ANALYSIS — expandable */}
      {showAI && ai_analysis && (
        <div className="shrink-0 max-h-56 overflow-y-auto bg-gray-900/70 border-t border-purple-600/30 px-5 py-3 space-y-2">
          <div className="flex items-center gap-3 mb-1.5">
            <h3 className="text-xs font-extrabold text-purple-400 uppercase tracking-widest">AI Analysis</h3>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-lg font-bold ${ai_analysis.sentiment === 'BULLISH' ? 'bg-green-900/40 text-green-400' : ai_analysis.sentiment === 'BEARISH' ? 'bg-red-900/40 text-red-400' : 'bg-gray-800 text-gray-300'}`}>{ai_analysis.sentiment}</span>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-lg font-bold ${ai_analysis.confidence === 'HIGH' ? 'bg-green-900/30 text-green-400' : ai_analysis.confidence === 'LOW' ? 'bg-red-900/30 text-red-400' : 'bg-yellow-900/30 text-yellow-400'}`}>{ai_analysis.confidence} conf</span>
          </div>
          <p className="text-xs text-gray-200 leading-relaxed">{ai_analysis.analysis || ai_analysis.summary}</p>
          {ai_analysis.bullets && ai_analysis.bullets.length > 0 && (
            <ul className="space-y-1">
              {ai_analysis.bullets.map((b, i) => <li key={i} className="text-[11px] text-gray-300 font-mono pl-3 border-l-2 border-cyan-600/40">{b}</li>)}
            </ul>
          )}
          {ai_analysis.risk_notes && ai_analysis.risk_notes.length > 0 && (
            <div className="pt-1.5 border-t border-gray-700/50">
              <p className="text-[10px] text-red-400 uppercase font-bold mb-1">⚠ Risk Notes</p>
              {ai_analysis.risk_notes.map((r, i) => <p key={i} className="text-[10px] text-red-300/90 font-mono">{r}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
