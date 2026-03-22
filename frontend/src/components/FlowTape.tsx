import type { FlowEntry } from '../hooks/useWebSocket'

const TYPE_CLR: Record<string, string> = { BUY: 'text-neon-green', SELL: 'text-neon-red', NEUTRAL: 'text-neon-yellow' }
const TYPE_BG: Record<string, string> = { BUY: 'bg-emerald-950/20', SELL: 'bg-red-950/20', NEUTRAL: 'bg-yellow-950/10' }

export default function FlowTape({ tape }: { tape: FlowEntry[] }) {
  const rev = [...tape].reverse()
  return (
    <div className="h-full flex flex-col">
      <h2 className="text-[11px] font-bold text-neon-purple uppercase tracking-widest mb-1.5 px-1">Options Flow Tape</h2>
      <div className="flex-1 overflow-y-auto font-mono text-[10px] space-y-px">
        {rev.length === 0 && <p className="text-tb-muted text-center py-2">No flow data</p>}
        {rev.map((f, i) => (
          <div key={i} className={`flex items-center gap-2 px-2 py-[3px] rounded ${TYPE_BG[f.type]}`}>
            <span className="text-tb-muted/50 w-14 shrink-0">{new Date(f.time).toLocaleTimeString('en-IN', { hour12: false })}</span>
            <span className="text-tb-muted w-8 shrink-0">{f.index.slice(0, 3)}</span>
            <span className="text-tb-text w-16 shrink-0">{f.strike}</span>
            <span className="text-tb-text w-12 text-right shrink-0">₹{f.price}</span>
            <span className="text-tb-muted w-14 text-right shrink-0">{f.volume.toLocaleString()}</span>
            <span className={`font-bold w-10 shrink-0 ${TYPE_CLR[f.type]}`}>{f.type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
