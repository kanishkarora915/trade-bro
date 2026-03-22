import type { DetectorResult } from '../hooks/useWebSocket'

const STATUS_CLR: Record<string, string> = {
  NORMAL: 'text-tb-muted', WATCH: 'text-neon-blue', ALERT: 'text-neon-orange', CRITICAL: 'text-neon-red'
}

export default function DetectorDetail({ detector, onClose }: { detector: DetectorResult; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-tb-card border border-tb-border rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-tb-text">{detector.name}</h2>
            <div className="flex items-center gap-3 mt-1">
              <span className={`text-xs font-bold ${STATUS_CLR[detector.status]}`}>{detector.status}</span>
              <span className="text-xs text-tb-muted">Score: {detector.score.toFixed(0)}/100</span>
              <span className="text-xs text-tb-text">{detector.metric}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-tb-muted hover:text-tb-text text-xl px-2">✕</button>
        </div>

        {/* Score bar */}
        <div className="h-2 bg-tb-border rounded-full overflow-hidden mb-4">
          <div className={`h-full rounded-full transition-all duration-500 ${
            detector.status === 'CRITICAL' ? 'bg-neon-red' : detector.status === 'ALERT' ? 'bg-neon-orange' :
            detector.status === 'WATCH' ? 'bg-neon-blue' : 'bg-tb-muted/40'
          }`} style={{ width: `${detector.score}%` }} />
        </div>

        {/* Alerts table */}
        {detector.alerts && detector.alerts.length > 0 ? (
          <div className="space-y-2">
            <h3 className="text-[11px] text-neon-cyan uppercase tracking-widest font-bold">Active Alerts</h3>
            {detector.alerts.map((alert: any, i: number) => (
              <div key={i} className="bg-tb-bg border border-tb-border rounded-xl p-3">
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono">
                  {Object.entries(alert).filter(([k]) => k !== 'score').map(([key, val]) => (
                    <div key={key} className="contents">
                      <span className="text-tb-muted uppercase text-[9px]">{key.replace(/_/g, ' ')}</span>
                      <span className={`text-tb-text ${
                        key === 'status' ? STATUS_CLR[val as string] || '' : ''
                      }`}>{String(val)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-tb-muted text-sm">
            No active alerts — detector is in NORMAL state
          </div>
        )}
      </div>
    </div>
  )
}
