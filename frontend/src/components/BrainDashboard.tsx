import ConfluentGauge from './ConfluentGauge'
import type { ConfluenceResult, BrainSignal } from '../hooks/useWebSocket'

export default function BrainDashboard({ confluence, brain, spot }: {
  confluence: ConfluenceResult; brain: BrainSignal; spot: number
}) {
  const dc = confluence.direction === 'BULLISH' ? 'text-neon-green' : confluence.direction === 'BEARISH' ? 'text-neon-red' : 'text-tb-muted'
  const arrow = confluence.direction === 'BULLISH' ? '▲' : confluence.direction === 'BEARISH' ? '▼' : '●'

  return (
    <div className="h-full flex flex-col">
      <div className="text-center border-b border-tb-border pb-3 mb-4">
        <h1 className="text-base font-extrabold tracking-[.15em] text-neon-cyan">TRADE BRO — LIVE</h1>
        <p className="text-[9px] text-tb-muted mt-0.5">Real-time Options Intelligence</p>
      </div>

      {/* Gauge + Direction */}
      <div className="flex items-center justify-center gap-5 mb-5">
        <ConfluentGauge score={confluence.score} status={confluence.status} color={confluence.color} />
        <div className="space-y-1.5">
          <p className="text-[9px] text-tb-muted uppercase tracking-widest">Direction</p>
          <p className={`text-2xl font-black ${dc}`}>{arrow} {confluence.direction}</p>
          <div className="flex items-center gap-2 text-[9px] text-tb-muted">
            <span>Mult: {confluence.time_multiplier}x</span>
            {confluence.is_expiry_day && <span className="text-neon-red font-bold bg-red-950/30 px-1.5 py-0.5 rounded">EXPIRY</span>}
          </div>
        </div>
      </div>

      {/* Primary Trade */}
      {brain.active && brain.primary ? (
        <div className="border border-neon-green/20 bg-emerald-950/10 rounded-xl p-4 mb-3 animate-slide-up">
          <div className="text-[10px] text-neon-green font-extrabold uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-neon-green rounded-full animate-pulse-dot" /> Primary Trade
          </div>
          <div className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-2 text-xs font-mono">
            <span className="text-tb-muted">BUY</span><span className="text-neon-green font-bold text-sm">{brain.primary.strike}</span>
            <span className="text-tb-muted">CMP</span><span className="text-tb-text font-semibold">{brain.primary.cmp}</span>
            <span className="text-tb-muted">TARGET 1</span><span className="text-neon-green">{brain.primary.target1}</span>
            <span className="text-tb-muted">TARGET 2</span><span className="text-neon-green">{brain.primary.target2}</span>
            <span className="text-tb-muted">STOP LOSS</span><span className="text-neon-red font-bold">{brain.primary.stop_loss}</span>
            <span className="text-tb-muted">TIME</span><span className="text-neon-yellow text-[10px]">{brain.primary.time_limit}</span>
          </div>
        </div>
      ) : (
        <div className="border border-tb-border rounded-xl p-5 mb-3 text-center">
          <p className="text-tb-muted text-sm">{brain.message || 'No signal — Score below 51'}</p>
          <p className="text-[9px] text-tb-muted/50 mt-1">Monitoring 17 detectors...</p>
        </div>
      )}

      {/* Secondary */}
      {brain.active && brain.secondary && (
        <div className="border border-neon-orange/15 bg-orange-950/8 rounded-xl p-3 mb-3">
          <div className="text-[9px] text-neon-orange font-bold uppercase tracking-widest mb-2">Secondary (OTM)</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono">
            <span className="text-tb-muted">BUY</span><span className="text-neon-orange">{brain.secondary.strike}</span>
            <span className="text-tb-muted">CMP</span><span>{brain.secondary.cmp}</span>
            <span className="text-tb-muted">TARGET</span><span className="text-neon-green">{brain.secondary.target}</span>
            <span className="text-tb-muted">SL</span><span className="text-neon-red">{brain.secondary.stop_loss}</span>
          </div>
        </div>
      )}

      {/* Firing Signals */}
      {brain.firing?.length > 0 && (
        <div className="border border-tb-border rounded-xl p-3 mb-3">
          <p className="text-[9px] text-tb-muted uppercase tracking-widest mb-2">Signals Firing</p>
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
      {brain.exit_rules?.length > 0 && (
        <div className="border border-tb-border rounded-xl p-2.5 space-y-0.5 mb-3">
          {brain.exit_rules.map((r, i) => (
            <p key={i} className="text-[9px] text-tb-muted"><span className="text-neon-yellow font-semibold">{r.rule}:</span> {r.detail}</p>
          ))}
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
