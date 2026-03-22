import type { DetectorResult } from '../hooks/useWebSocket'

const CFG: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  NORMAL: { border: 'border-tb-border', bg: 'bg-tb-card', text: 'text-tb-muted', dot: 'bg-tb-muted' },
  WATCH: { border: 'border-neon-blue/40', bg: 'bg-blue-950/15', text: 'text-neon-blue', dot: 'bg-neon-blue' },
  ALERT: { border: 'border-neon-orange/40', bg: 'bg-orange-950/15', text: 'text-neon-orange', dot: 'bg-neon-orange' },
  CRITICAL: { border: 'border-neon-red/50', bg: 'bg-red-950/20', text: 'text-neon-red', dot: 'bg-neon-red' },
}
const BAR: Record<string, string> = { NORMAL: 'bg-tb-muted/40', WATCH: 'bg-neon-blue', ALERT: 'bg-neon-orange', CRITICAL: 'bg-neon-red' }

export default function DetectorCard({ d }: { d: DetectorResult }) {
  const s = d.status || 'NORMAL'
  const c = CFG[s]
  return (
    <div className={`${c.bg} border ${c.border} rounded-xl p-3 transition-all duration-300 hover:brightness-110`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wider text-tb-text/80 truncate">{d.name}</span>
        <span className={`w-2 h-2 rounded-full ${c.dot} ${s === 'CRITICAL' ? 'animate-pulse-dot' : ''}`} />
      </div>
      <div className="text-xs font-mono text-tb-text font-medium truncate mb-1.5">{d.metric}</div>
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-[10px] font-bold ${c.text}`}>{s}</span>
        <span className="text-[10px] text-tb-muted font-mono">{d.score.toFixed(0)}</span>
      </div>
      <div className="h-1 bg-tb-border rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${BAR[s]}`} style={{ width: `${d.score}%` }} />
      </div>
    </div>
  )
}
