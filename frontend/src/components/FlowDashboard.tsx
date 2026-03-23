import { useState } from 'react'
import type { TradeState, DetectorResult } from '../hooks/useWebSocket'

interface Props { state: TradeState; onBack: () => void }

const TYPE_CLR: Record<string, string> = { BUY: 'text-neon-green', SELL: 'text-neon-red', NEUTRAL: 'text-tb-muted' }
const TYPE_BG: Record<string, string> = { BUY: 'bg-emerald-950/20 border-emerald-800/20', SELL: 'bg-red-950/20 border-red-800/20', NEUTRAL: 'bg-tb-surface/20 border-tb-border' }
const STR_CLR: Record<string, string> = { AGGRESSIVE: 'bg-neon-red/20 text-neon-red', STRONG: 'bg-neon-green/20 text-neon-green', MILD: 'bg-neon-yellow/20 text-neon-yellow' }
const DET_CLR: Record<string, string> = { CRITICAL: 'text-neon-green', ALERT: 'text-neon-green', WATCH: 'text-neon-yellow', NORMAL: 'text-tb-muted' }
const DET_BAR: Record<string, string> = { CRITICAL: 'bg-neon-green', ALERT: 'bg-neon-green', WATCH: 'bg-neon-yellow', NORMAL: 'bg-tb-muted/30' }

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
  const vixClr = india_vix ? (india_vix > 20 ? 'text-neon-red' : india_vix > 14 ? 'text-neon-yellow' : 'text-neon-green') : ''
  const dirClr = confluence.direction === 'BULLISH' ? 'text-neon-green' : confluence.direction === 'BEARISH' ? 'text-neon-red' : 'text-tb-muted'

  return (
    <div className="h-screen flex flex-col bg-tb-bg overflow-hidden">
      {/* SECTION 1: LIVE TRADE SIGNAL — top banner */}
      <div className={`shrink-0 border-b ${sig ? 'border-neon-green/30 bg-emerald-950/10' : 'border-tb-border bg-tb-card/30'}`}>
        <div className="flex items-center justify-between px-4 py-1.5">
          <div className="flex items-center gap-3">
            <button onClick={onBack} className="text-neon-cyan hover:text-neon-cyan/80 text-sm font-bold">← Main</button>
            <span className="text-tb-border">|</span>
            <h1 className="text-sm font-extrabold tracking-widest text-neon-purple uppercase">Flow Dashboard</h1>
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono">
            <span className="text-tb-muted">SPOT <span className="text-tb-text font-bold">{spot.toLocaleString('en-IN')}</span></span>
            <span className="text-tb-muted">ATM <span className="text-neon-cyan font-bold">{atm}</span></span>
          </div>
        </div>
        <div className="px-4 pb-2">
          {sig && sig.primary ? (
            <div className="flex items-center gap-6 flex-wrap">
              <div className="flex items-center gap-2">
                <span className={`text-xl font-black ${sig.direction === 'BULLISH' ? 'text-neon-green' : 'text-neon-red'}`}>
                  {sig.primary.action} {sig.primary.strike}
                </span>
                {sig.strength && <span className={`text-[9px] px-2 py-0.5 rounded font-bold ${STR_CLR[sig.strength] || 'bg-tb-surface text-tb-muted'}`}>{sig.strength}</span>}
              </div>
              <div className="flex items-center gap-4 text-[11px] font-mono">
                <span className="text-tb-muted">CMP <span className="text-tb-text font-bold">{sig.primary.cmp}</span></span>
                <span className="text-tb-muted">T1 <span className="text-neon-green font-bold">{sig.primary.target1}</span></span>
                <span className="text-tb-muted">T2 <span className="text-neon-green font-bold">{sig.primary.target2}</span></span>
                <span className="text-tb-muted">SL <span className="text-neon-red font-bold">{sig.primary.stop_loss}</span></span>
                <span className="text-tb-muted">TL <span className="text-neon-yellow">{sig.primary.time_limit}</span></span>
              </div>
              {sig.secondary && (
                <span className="text-[10px] font-mono text-neon-orange">ALT: {sig.secondary.action} {sig.secondary.strike} @ {sig.secondary.cmp}</span>
              )}
            </div>
          ) : (
            <p className="text-tb-muted text-[11px] font-mono">Monitoring... No active signal &mdash; Score: {confluence.score.toFixed(0)}/100</p>
          )}
        </div>
      </div>

      {/* MAIN 3-COL GRID */}
      <div className="flex-1 grid grid-cols-[280px_1fr_260px] gap-[1px] bg-tb-border overflow-hidden">

        {/* SECTION 2: SIGNAL HISTORY — left column */}
        <div className="bg-tb-bg p-2 flex flex-col overflow-hidden">
          <h2 className="text-[10px] font-bold text-neon-green uppercase tracking-widest mb-1.5 shrink-0">Signal History</h2>
          <div className="flex-1 overflow-y-auto font-mono text-[9px]">
            <div className="grid grid-cols-[44px_28px_20px_52px_40px_36px_28px_auto] gap-x-1 px-1 py-1 text-tb-muted/50 uppercase sticky top-0 bg-tb-bg border-b border-tb-border">
              <span>Time</span><span>Idx</span><span>Dir</span><span>Strike</span><span>Entry</span><span>Target</span><span>SL</span><span>Spot</span>
            </div>
            {history.length === 0 && <p className="text-tb-muted text-center py-6 text-[10px]">No signals yet</p>}
            {history.map((s, i) => {
              const bull = s.direction === 'BULLISH'
              return (
                <div key={i} className={`grid grid-cols-[44px_28px_20px_52px_40px_36px_28px_auto] gap-x-1 px-1 py-[4px] border-b border-tb-border/20 ${bull ? 'text-neon-green/80' : 'text-neon-red/80'}`}>
                  <span className="text-tb-muted/60">{s.recorded_at ? new Date(s.recorded_at).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' }) : '--'}</span>
                  <span className="text-tb-muted">{(s.index || '').slice(0, 3)}</span>
                  <span className="font-bold">{bull ? '▲' : '▼'}</span>
                  <span className="font-bold text-tb-text">{s.primary?.strike || '—'}</span>
                  <span>{s.primary?.cmp || '—'}</span>
                  <span className="text-neon-green">{s.primary?.target1 || '—'}</span>
                  <span className="text-neon-red">{s.primary?.stop_loss || '—'}</span>
                  <span className="text-tb-muted">{s.spot_at_signal?.toLocaleString('en-IN') || '—'}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* SECTION 3: DETAILED FLOW TAPE — center, scrollable */}
        <div className="bg-tb-bg p-2 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-1.5 shrink-0">
            <h2 className="text-[10px] font-bold text-neon-purple uppercase tracking-widest">Options Flow Tape</h2>
            <div className="flex items-center gap-1">
              {(['ALL', 'BUY', 'SELL'] as const).map(f => (
                <button key={f} onClick={() => setFilter(f)} className={`text-[9px] px-2 py-0.5 rounded font-bold transition-all ${filter === f ? (f === 'BUY' ? 'bg-emerald-900/50 text-neon-green' : f === 'SELL' ? 'bg-red-900/50 text-neon-red' : 'bg-tb-surface text-neon-cyan') : 'text-tb-muted hover:text-tb-text'}`}>{f}</button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 px-1 py-1 text-[8px] text-tb-muted/50 uppercase font-mono border-b border-tb-border shrink-0">
            <span className="w-14">Time</span><span className="w-8">Idx</span><span className="w-20">Strike</span>
            <span className="w-14 text-right">Price</span><span className="w-14 text-right">Vol</span>
            <span className="w-16 text-right">OI</span><span className="w-20 text-right">Value(₹)</span><span className="w-12">Type</span>
          </div>
          <div className="flex-1 overflow-y-auto font-mono text-[10px] space-y-px">
            {filtered.length === 0 && <p className="text-tb-muted text-center py-8">No flow data yet</p>}
            {filtered.map((f, i) => {
              const val = f.price * f.volume * 25 // estimated lot_size
              return (
                <div key={i} className={`flex items-center gap-2 px-1 py-[4px] rounded border-l-2 ${TYPE_BG[f.type]} hover:bg-tb-surface/20`}>
                  <span className="text-tb-muted/50 w-14">{new Date(f.time).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  <span className="text-tb-muted w-8">{(f.index || '').slice(0, 3)}</span>
                  <span className="text-tb-text font-semibold w-20">{f.strike}</span>
                  <span className="text-tb-text w-14 text-right">₹{f.price.toFixed(1)}</span>
                  <span className={`w-14 text-right ${f.volume > 5000 ? 'text-neon-yellow font-bold' : 'text-tb-muted'}`}>{f.volume.toLocaleString()}</span>
                  <span className="text-tb-muted w-16 text-right">{f.oi.toLocaleString()}</span>
                  <span className="text-tb-muted w-20 text-right">{val > 1e7 ? `${(val / 1e7).toFixed(1)}Cr` : val > 1e5 ? `${(val / 1e5).toFixed(1)}L` : val.toLocaleString()}</span>
                  <span className={`font-bold w-12 ${TYPE_CLR[f.type]}`}>{f.type === 'BUY' ? '▲ BUY' : f.type === 'SELL' ? '▼ SELL' : '—'}</span>
                </div>
              )
            })}
          </div>
          <div className="shrink-0 flex items-center justify-between mt-1 pt-1 border-t border-tb-border text-[9px] font-mono">
            <span className="text-tb-muted">{filtered.length} entries</span>
            <div className="flex gap-3">
              <span className="text-neon-green">BUY {(tape || []).filter(t => t.type === 'BUY').length}</span>
              <span className="text-neon-red">SELL {(tape || []).filter(t => t.type === 'SELL').length}</span>
            </div>
          </div>
        </div>

        {/* SECTION 4: DETECTOR BREAKDOWN — right column */}
        <div className="bg-tb-bg p-2 flex flex-col overflow-hidden">
          <h2 className="text-[10px] font-bold text-neon-cyan uppercase tracking-widest mb-1.5 shrink-0">Detectors ({detList.length})</h2>
          <div className="flex-1 overflow-y-auto space-y-1">
            {detList.length === 0 && <p className="text-tb-muted text-[10px] text-center py-6">No detector data</p>}
            {detList.map((d: DetectorResult) => (
              <div key={d.id} className="border border-tb-border/40 rounded-lg p-1.5 hover:bg-tb-surface/20 cursor-pointer transition-colors" onClick={() => setExpandedDet(expandedDet === d.id ? null : d.id)}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[9px] font-bold text-tb-text truncate max-w-[140px]">{d.name}</span>
                  <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${DET_CLR[d.status]} bg-tb-surface/50`}>{d.status}</span>
                </div>
                <div className="flex items-center gap-1.5 mb-0.5">
                  <div className="flex-1 h-1 bg-tb-surface rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${DET_BAR[d.status]}`} style={{ width: `${Math.min(d.score, 100)}%` }} />
                  </div>
                  <span className="text-[8px] font-mono text-tb-muted w-6 text-right">{d.score}</span>
                </div>
                <p className="text-[8px] text-tb-muted/70 truncate">{d.metric}</p>
                {expandedDet === d.id && d.alerts && d.alerts.length > 0 && (
                  <div className="mt-1 pt-1 border-t border-tb-border/30 space-y-0.5">
                    {d.alerts.slice(0, 5).map((a: any, i: number) => (
                      <p key={i} className="text-[8px] text-neon-yellow/80">{typeof a === 'string' ? a : JSON.stringify(a)}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SECTION 5: MARKET CONTEXT — bottom bar */}
      <div className="shrink-0 flex items-center justify-between px-4 py-1.5 bg-tb-card/40 border-t border-tb-border text-[10px] font-mono">
        <div className="flex items-center gap-4">
          {india_vix != null && (
            <span className="text-tb-muted">VIX <span className={`font-bold ${vixClr}`}>{india_vix.toFixed(2)}</span> <span className={`text-[8px] ${vixClr}`}>{vixLabel}</span></span>
          )}
          {fii_dii && (
            <>
              <span className="text-tb-muted">FII <span className={`font-bold ${(fii_dii.fii_net_cr || 0) >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>{(fii_dii.fii_net_cr || 0) >= 0 ? '+' : ''}{fii_dii.fii_net_cr?.toFixed(0)}Cr</span></span>
              <span className="text-tb-muted">DII <span className={`font-bold ${(fii_dii.dii_net_cr || 0) >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>{(fii_dii.dii_net_cr || 0) >= 0 ? '+' : ''}{fii_dii.dii_net_cr?.toFixed(0)}Cr</span></span>
            </>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className={`font-bold ${dirClr}`}>{confluence.direction} {confluence.score.toFixed(0)}/100</span>
          <span className="text-tb-muted">IDX <span className="text-neon-cyan font-bold">{state.active_index || 'NIFTY'}</span></span>
          <span className="text-tb-muted">SPOT <span className="text-tb-text font-bold">{spot.toLocaleString('en-IN')}</span></span>
        </div>
        <button onClick={() => setShowAI(!showAI)} className={`text-[9px] px-2 py-0.5 rounded font-bold transition-all ${showAI ? 'bg-neon-purple/20 text-neon-purple' : 'text-tb-muted hover:text-neon-purple border border-tb-border'}`}>
          {showAI ? 'Hide AI' : 'AI Analysis'}
        </button>
      </div>

      {/* SECTION 6: AI ANALYSIS — expandable */}
      {showAI && ai_analysis && (
        <div className="shrink-0 max-h-52 overflow-y-auto bg-tb-card/60 border-t border-neon-purple/20 px-4 py-3 space-y-2">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-[11px] font-extrabold text-neon-purple uppercase tracking-widest">AI Analysis</h3>
            <span className={`text-[9px] px-2 py-0.5 rounded font-bold ${ai_analysis.sentiment === 'BULLISH' ? 'bg-neon-green/20 text-neon-green' : ai_analysis.sentiment === 'BEARISH' ? 'bg-neon-red/20 text-neon-red' : 'bg-tb-surface text-tb-muted'}`}>{ai_analysis.sentiment}</span>
            <span className={`text-[9px] px-2 py-0.5 rounded font-bold ${ai_analysis.confidence === 'HIGH' ? 'bg-neon-green/15 text-neon-green' : ai_analysis.confidence === 'LOW' ? 'bg-neon-red/15 text-neon-red' : 'bg-neon-yellow/15 text-neon-yellow'}`}>{ai_analysis.confidence} conf</span>
          </div>
          <p className="text-[11px] text-tb-text leading-relaxed">{ai_analysis.analysis || ai_analysis.summary}</p>
          {ai_analysis.bullets && ai_analysis.bullets.length > 0 && (
            <ul className="space-y-0.5">
              {ai_analysis.bullets.map((b, i) => <li key={i} className="text-[10px] text-tb-muted/80 font-mono pl-2 border-l border-neon-cyan/20">{b}</li>)}
            </ul>
          )}
          {ai_analysis.risk_notes && ai_analysis.risk_notes.length > 0 && (
            <div className="pt-1 border-t border-tb-border/30">
              <p className="text-[9px] text-neon-red/60 uppercase font-bold mb-0.5">Risk Notes</p>
              {ai_analysis.risk_notes.map((r, i) => <p key={i} className="text-[9px] text-neon-red/70 font-mono">{r}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
