export default function ConfluentGauge({ score, status, color }: { score: number; status: string; color: string }) {
  const R = 58, C = 2 * Math.PI * R, off = C - (score / 100) * C
  const sc = color === 'red' ? '#ff2244' : color === 'orange' ? '#ff8c00' : color === 'yellow' ? '#ffd700' : color === 'blue' ? '#3388ff' : '#2a2a40'
  const glow = score >= 86 ? 'shadow-[0_0_30px_rgba(255,34,68,0.3)]' : score >= 76 ? 'shadow-[0_0_30px_rgba(0,255,136,0.2)]' : ''

  return (
    <div className={`flex flex-col items-center rounded-2xl p-4 ${glow} transition-shadow duration-1000`}>
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={R} fill="none" stroke="#1a1a2e" strokeWidth="8" />
        <circle cx="70" cy="70" r={R} fill="none" stroke={sc} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={C} strokeDashoffset={off} transform="rotate(-90 70 70)"
          className="transition-all duration-1000" style={{ filter: `drop-shadow(0 0 10px ${sc})` }} />
        <text x="70" y="64" textAnchor="middle" fill="#e8e8f0" fontSize="34" fontWeight="800" fontFamily="Inter">
          {score.toFixed(0)}
        </text>
        <text x="70" y="84" textAnchor="middle" fill="#6b6b80" fontSize="11" fontFamily="JetBrains Mono">/ 100</text>
      </svg>
      <div className={`mt-1 text-xs font-extrabold tracking-widest ${
        color === 'red' ? 'text-neon-red' : color === 'orange' ? 'text-neon-orange' : color === 'yellow' ? 'text-neon-yellow' : color === 'blue' ? 'text-neon-blue' : 'text-tb-muted'
      }`}>{status}</div>
    </div>
  )
}
