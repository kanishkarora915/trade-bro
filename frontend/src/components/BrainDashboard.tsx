import { useState } from 'react'
import ConfluentGauge from './ConfluentGauge'
import type { ConfluenceResult, BrainSignal, AIAnalysis, SignalHistoryEntry, FiiDiiData } from '../hooks/useWebSocket'

export default function BrainDashboard({ confluence, brain, spot, aiAnalysis, signalHistory, lastSignal, fiiDii, tickerActive, state }: {
  confluence: ConfluenceResult; brain: BrainSignal; spot: number
  aiAnalysis?: AIAnalysis; signalHistory?: SignalHistoryEntry[]
  lastSignal?: BrainSignal | null; fiiDii?: FiiDiiData; tickerActive?: boolean
  state?: any
}) {
  const [showHistory, setShowHistory] = useState(false)
  const dc = confluence.direction === 'BULLISH' ? 'text-neon-green' : confluence.direction === 'BEARISH' ? 'text-neon-red' : 'text-tb-muted'
  const arrow = confluence.direction === 'BULLISH' ? '▲' : confluence.direction === 'BEARISH' ? '▼' : '●'

  // Always show a signal: active brain signal OR last known signal
  const displaySignal = brain.active ? brain : lastSignal
  const isStale = !brain.active && lastSignal?.active

  return (
    <div className="h-full flex flex-col gap-2 overflow-y-auto">
      {/* Header */}
      <div className="text-center border-b border-tb-border pb-2">
        <h1 className="text-base font-extrabold tracking-[.15em] text-neon-cyan">TRADE BRO — LIVE</h1>
        <div className="flex items-center justify-center gap-3 mt-0.5">
          <p className="text-[9px] text-tb-muted">Real-time Options Intelligence</p>
          {tickerActive && (
            <span className="text-[8px] text-neon-green font-bold bg-emerald-950/30 px-1.5 py-0.5 rounded flex items-center gap-1">
              <span className="w-1 h-1 bg-neon-green rounded-full animate-pulse-dot" />TICK
            </span>
          )}
        </div>
      </div>

      {/* Gauge + Direction */}
      <div className="flex items-center justify-center gap-5 mb-1">
        <ConfluentGauge score={confluence.score} status={confluence.status} color={confluence.color} />
        <div className="space-y-1">
          <p className="text-[9px] text-tb-muted uppercase tracking-widest">Direction</p>
          <p className={`text-2xl font-black ${dc}`}>{arrow} {confluence.direction}</p>
          <div className="flex items-center gap-2 text-[9px] text-tb-muted">
            <span>Mult: {confluence.time_multiplier}x</span>
            {confluence.is_expiry_day && <span className="text-neon-red font-bold bg-red-950/30 px-1.5 py-0.5 rounded">EXPIRY</span>}
          </div>
        </div>
      </div>

      {/* FII/DII Strip */}
      {fiiDii && (fiiDii.fii_net_cr !== 0 || fiiDii.dii_net_cr !== 0) && (
        <div className="flex items-center gap-3 px-3 py-1.5 bg-tb-card/30 rounded-lg border border-tb-border text-[10px] font-mono">
          <span className="text-tb-muted">FII</span>
          <span className={fiiDii.fii_net_cr >= 0 ? 'text-neon-green font-bold' : 'text-neon-red font-bold'}>
            ₹{fiiDii.fii_net_cr >= 0 ? '+' : ''}{fiiDii.fii_net_cr.toLocaleString('en-IN')} Cr
          </span>
          <span className="text-tb-border">|</span>
          <span className="text-tb-muted">DII</span>
          <span className={fiiDii.dii_net_cr >= 0 ? 'text-neon-green font-bold' : 'text-neon-red font-bold'}>
            ₹{fiiDii.dii_net_cr >= 0 ? '+' : ''}{fiiDii.dii_net_cr.toLocaleString('en-IN')} Cr
          </span>
        </div>
      )}

      {/* AI Analysis Bot */}
      {aiAnalysis && aiAnalysis.summary && (
        <div className="border border-purple-500/20 bg-purple-950/10 rounded-xl p-3 animate-slide-up">
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-[10px] font-extrabold uppercase tracking-widest text-purple-400">AI Analysis</span>
            <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${
              aiAnalysis.confidence === 'HIGH' ? 'bg-neon-green/20 text-neon-green' :
              aiAnalysis.confidence === 'MEDIUM' ? 'bg-neon-yellow/20 text-neon-yellow' :
              'bg-tb-muted/20 text-tb-muted'
            }`}>{aiAnalysis.confidence}</span>
            <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${
              aiAnalysis.sentiment === 'BULLISH' ? 'bg-neon-green/20 text-neon-green' :
              aiAnalysis.sentiment === 'BEARISH' ? 'bg-neon-red/20 text-neon-red' :
              'bg-tb-muted/20 text-tb-muted'
            }`}>{aiAnalysis.sentiment}</span>
          </div>

          {/* Summary headline */}
          <p className="text-[11px] text-tb-text font-semibold leading-snug mb-2">{aiAnalysis.summary}</p>

          {/* Bullet points */}
          {aiAnalysis.bullets?.length > 0 && (
            <div className="space-y-0.5 mb-2">
              {aiAnalysis.bullets.slice(0, 5).map((b, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[10px]">
                  <span className="text-purple-400 mt-0.5 shrink-0">•</span>
                  <span className="text-tb-muted leading-snug">{b}</span>
                </div>
              ))}
            </div>
          )}

          {/* Full analysis (collapsed by default) */}
          <details className="group">
            <summary className="text-[9px] text-purple-400 cursor-pointer hover:text-purple-300 transition-colors">
              Full analysis ▸
            </summary>
            <p className="text-[10px] text-tb-muted/80 leading-relaxed mt-1.5 whitespace-pre-line">{aiAnalysis.analysis}</p>
          </details>

          {/* Risk notes */}
          {aiAnalysis.risk_notes?.length > 0 && (
            <div className="mt-2 pt-2 border-t border-purple-500/10">
              <p className="text-[8px] text-neon-red/70 uppercase tracking-widest mb-1">Risk Notes</p>
              {aiAnalysis.risk_notes.map((r, i) => (
                <p key={i} className="text-[9px] text-neon-red/60 leading-snug">⚠ {r}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Primary Trade — ALWAYS VISIBLE */}
      {displaySignal?.active && displaySignal.primary ? (
        <div className={`border rounded-xl p-3 animate-slide-up ${
          isStale
            ? 'border-tb-border bg-tb-card/20 opacity-80'
            : 'border-neon-green/20 bg-emerald-950/10'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] font-extrabold uppercase tracking-widest flex items-center gap-1.5">
              {isStale ? (
                <span className="text-neon-yellow">
                  <span className="w-1.5 h-1.5 bg-neon-yellow rounded-full inline-block mr-1" />LAST SIGNAL
                </span>
              ) : (
                <span className="text-neon-green">
                  <span className="w-1.5 h-1.5 bg-neon-green rounded-full animate-pulse-dot inline-block mr-1" />LIVE TRADE
                </span>
              )}
            </div>
            {isStale && displaySignal.timestamp && (
              <span className="text-[8px] text-tb-muted">
                {new Date(displaySignal.timestamp).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            {displaySignal.strength && (
              <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${
                displaySignal.strength === 'EXTREME' ? 'bg-neon-red/20 text-neon-red' :
                displaySignal.strength === 'STRONG' ? 'bg-neon-green/20 text-neon-green' :
                'bg-neon-yellow/20 text-neon-yellow'
              }`}>{displaySignal.strength}</span>
            )}
          </div>
          <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs font-mono">
            <span className="text-tb-muted">BUY</span><span className="text-neon-green font-bold text-sm">{displaySignal.primary.strike}</span>
            <span className="text-tb-muted">CMP</span><span className="text-tb-text font-semibold">{displaySignal.primary.cmp}</span>
            <span className="text-tb-muted">TARGET 1</span><span className="text-neon-green">{displaySignal.primary.target1}</span>
            <span className="text-tb-muted">TARGET 2</span><span className="text-neon-green">{displaySignal.primary.target2}</span>
            <span className="text-tb-muted">STOP LOSS</span><span className="text-neon-red font-bold">{displaySignal.primary.stop_loss}</span>
            <span className="text-tb-muted">TIME</span><span className="text-neon-yellow text-[10px]">{displaySignal.primary.time_limit}</span>
          </div>
        </div>
      ) : (
        <div className="border border-tb-border rounded-xl p-4 text-center">
          <p className="text-tb-muted text-sm">{brain.message || 'No signal — Score below 51'}</p>
          <p className="text-[9px] text-tb-muted/50 mt-1">Monitoring 17 detectors...</p>
        </div>
      )}

      {/* Secondary */}
      {displaySignal?.active && displaySignal.secondary && !isStale && (
        <div className="border border-neon-orange/15 bg-orange-950/8 rounded-xl p-2.5">
          <div className="text-[9px] text-neon-orange font-bold uppercase tracking-widest mb-1.5">Secondary (OTM)</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] font-mono">
            <span className="text-tb-muted">BUY</span><span className="text-neon-orange">{displaySignal.secondary.strike}</span>
            <span className="text-tb-muted">CMP</span><span>{displaySignal.secondary.cmp}</span>
            <span className="text-tb-muted">TARGET</span><span className="text-neon-green">{displaySignal.secondary.target}</span>
            <span className="text-tb-muted">SL</span><span className="text-neon-red">{displaySignal.secondary.stop_loss}</span>
          </div>
        </div>
      )}

      {/* OTM Trades — Aggressive Opportunities */}
      {(state as any).otm_trades?.length > 0 && !isStale && (
        <div className="border border-yellow-700/20 bg-yellow-950/10 rounded-xl p-2.5">
          <div className="text-[9px] text-yellow-400 font-bold uppercase tracking-widest mb-1.5">🎯 OTM Opportunities (High Risk/Reward)</div>
          <div className="space-y-1.5">
            {(state as any).otm_trades.map((t: any, i: number) => (
              <div key={i} className="flex items-center justify-between text-[11px] font-mono bg-black/20 rounded-lg px-2 py-1.5">
                <span className="text-yellow-400 font-bold w-20">{t.strike}</span>
                <span className="text-white">₹{t.cmp}</span>
                <span className="text-green-400">T1: ₹{t.target1}</span>
                <span className="text-green-400">T2: ₹{t.target2}</span>
                <span className="text-red-400">SL: ₹{t.stop_loss}</span>
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${t.risk === 'HIGH' ? 'bg-red-900/40 text-red-400' : 'bg-yellow-900/40 text-yellow-400'}`}>{t.risk}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Firing Signals */}
      {brain.firing?.length > 0 && (
        <div className="border border-tb-border rounded-xl p-2.5">
          <p className="text-[9px] text-tb-muted uppercase tracking-widest mb-1.5">Signals Firing</p>
          {brain.firing.slice(0, 6).map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px] py-0.5">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${f.status === 'CRITICAL' ? 'bg-neon-red' : f.status === 'ALERT' ? 'bg-neon-orange' : 'bg-neon-blue'}`} />
              <span className="text-tb-text truncate">{f.name}</span>
              <span className="text-tb-muted ml-auto text-[9px] shrink-0">{f.metric}</span>
            </div>
          ))}
        </div>
      )}

      {/* Exit Rules */}
      {brain.exit_rules?.length > 0 && !isStale && (
        <div className="border border-tb-border rounded-xl p-2 space-y-0.5">
          {brain.exit_rules.map((r, i) => (
            <p key={i} className="text-[9px] text-tb-muted"><span className="text-neon-yellow font-semibold">{r.rule}:</span> {r.detail}</p>
          ))}
        </div>
      )}

      {/* Signal History */}
      {signalHistory && signalHistory.length > 0 && (
        <div className="border border-tb-border rounded-xl p-2.5">
          <button onClick={() => setShowHistory(!showHistory)}
            className="w-full flex items-center justify-between text-[9px] text-tb-muted uppercase tracking-widest">
            <span>Signal History ({signalHistory.length})</span>
            <span className="text-neon-cyan">{showHistory ? '▾' : '▸'}</span>
          </button>
          {showHistory && (
            <div className="mt-2 space-y-1.5 max-h-40 overflow-y-auto">
              {[...signalHistory].reverse().map((sig, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px] py-1 border-b border-tb-border/30 last:border-0">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${sig.direction === 'BULLISH' ? 'bg-neon-green' : 'bg-neon-red'}`} />
                  <span className="text-tb-text font-mono">{sig.primary?.strike || '?'}</span>
                  <span className="text-tb-muted">@</span>
                  <span className="text-tb-text font-mono">{sig.primary?.cmp || '?'}</span>
                  <span className="text-tb-muted ml-auto text-[8px]">
                    {sig.recorded_at ? new Date(sig.recorded_at).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' }) : ''}
                  </span>
                  <span className={`text-[8px] font-bold ${sig.direction === 'BULLISH' ? 'text-neon-green' : 'text-neon-red'}`}>
                    {sig.direction === 'BULLISH' ? '▲' : '▼'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-auto pt-2 border-t border-tb-border flex justify-between text-[9px] text-tb-muted font-mono">
        <span>NIFTY {spot ? spot.toLocaleString('en-IN') : '—'}</span>
        <span>{new Date().toLocaleTimeString('en-IN', { hour12: false })}</span>
      </div>
    </div>
  )
}
