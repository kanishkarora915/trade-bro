import type { AlertEntry } from '../hooks/useWebSocket'

const TC: Record<string, string> = { CRITICAL: 'text-neon-red', ALERT: 'text-neon-orange', SIGNAL: 'text-neon-green', WATCH: 'text-neon-blue' }

export default function AlertLog({ alerts }: { alerts: AlertEntry[] }) {
  const rev = [...alerts].reverse()
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-1.5 px-1">
        <h2 className="text-[11px] font-bold text-neon-cyan uppercase tracking-widest">Alert Log</h2>
        <span className="text-[9px] font-mono text-tb-muted">{alerts.length} events</span>
      </div>
      <div className="flex-1 overflow-y-auto font-mono text-[11px]">
        {rev.length === 0 && <p className="text-tb-muted text-center py-3 text-xs">Monitoring — No alerts yet</p>}
        {rev.map((a, i) => {
          const t = new Date(a.time).toLocaleTimeString('en-IN', { hour12: false })
          return (
            <div key={i} className="flex gap-2 px-2 py-[3px] rounded hover:bg-tb-surface/30 transition-colors">
              <span className="text-tb-muted/60 shrink-0">{t}</span>
              <span className={`shrink-0 font-bold ${TC[a.type] || 'text-tb-muted'}`}>{a.type}</span>
              <span className="text-tb-text/70 truncate">{a.message}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
