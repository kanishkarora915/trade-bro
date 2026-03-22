const TABS = [
  { id: 'NIFTY', label: 'NIFTY 50', color: 'text-neon-cyan' },
  { id: 'BANKNIFTY', label: 'BANK NIFTY', color: 'text-neon-green' },
  { id: 'SENSEX', label: 'SENSEX', color: 'text-neon-orange' },
]

export default function IndexTabs({ active, spots, onSwitch }: {
  active: string; spots: Record<string, number>; onSwitch: (id: string) => void
}) {
  return (
    <div className="flex items-center gap-1">
      {TABS.map(t => (
        <button key={t.id} onClick={() => onSwitch(t.id)}
          className={`px-3 py-1.5 rounded-lg text-[11px] font-bold tracking-wider transition-all ${
            active === t.id
              ? `bg-tb-surface border border-neon-cyan/30 ${t.color}`
              : 'text-tb-muted hover:text-tb-text hover:bg-tb-surface/50 border border-transparent'
          }`}>
          {t.label}
          {spots[t.id] > 0 && (
            <span className={`ml-1.5 font-mono text-[10px] ${active === t.id ? t.color : 'text-tb-muted'}`}>
              {spots[t.id].toLocaleString('en-IN', { minimumFractionDigits: 1 })}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
