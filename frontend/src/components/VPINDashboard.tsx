import { useState } from 'react'

const SIGNAL_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  EXTREME: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/40' },
  HIGH: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40' },
  ELEVATED: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/40' },
  NEUTRAL: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30' },
}

const SIGNAL_ADVICE: Record<string, string> = {
  EXTREME: 'Avoid longs, hedge immediately. Institutional flow detected.',
  HIGH: 'Reduce position size, trail SL tight. Informed activity building.',
  ELEVATED: 'Watch closely. Informed activity starting to build.',
  NEUTRAL: 'Normal conditions. Safe to trade with standard risk.',
}

function VPINGauge({ value, size = 120 }: { value: number; size?: number }) {
  const pct = Math.min(1, Math.max(0, value))
  const angle = -90 + pct * 180
  const r = size / 2 - 8
  const cx = size / 2
  const cy = size / 2

  // Arc segments
  const segments = [
    { start: -90, end: 9, color: '#0A84FF' },    // NEUTRAL 0-0.55
    { start: 9, end: 63, color: '#EAB308' },      // ELEVATED 0.55-0.70
    { start: 63, end: 117, color: '#F97316' },     // HIGH 0.70-0.85
    { start: 117, end: 180, color: '#EF4444' },    // EXTREME 0.85+
  ]

  const arcPath = (startDeg: number, endDeg: number, radius: number) => {
    const s = (startDeg * Math.PI) / 180
    const e = (endDeg * Math.PI) / 180
    const x1 = cx + radius * Math.cos(s)
    const y1 = cy + radius * Math.sin(s)
    const x2 = cx + radius * Math.cos(e)
    const y2 = cy + radius * Math.sin(e)
    const large = endDeg - startDeg > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`
  }

  // Needle
  const needleAngle = (angle * Math.PI) / 180
  const nx = cx + (r - 15) * Math.cos(needleAngle)
  const ny = cy + (r - 15) * Math.sin(needleAngle)

  return (
    <svg width={size} height={size / 2 + 15} viewBox={`0 0 ${size} ${size / 2 + 15}`}>
      {segments.map((seg, i) => (
        <path key={i} d={arcPath(seg.start - 90, seg.end - 90, r)} fill="none" stroke={seg.color} strokeWidth={6} strokeLinecap="round" opacity={0.3} />
      ))}
      {/* Active arc */}
      <path d={arcPath(-180, angle - 90, r)} fill="none" stroke={pct >= 0.85 ? '#EF4444' : pct >= 0.70 ? '#F97316' : pct >= 0.55 ? '#EAB308' : '#0A84FF'} strokeWidth={6} strokeLinecap="round" />
      {/* Needle */}
      <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="white" strokeWidth={2} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={3} fill="white" />
      {/* Value text */}
      <text x={cx} y={cy + 14} textAnchor="middle" fill="white" fontSize="16" fontWeight="900" fontFamily="JetBrains Mono, monospace">
        {(pct * 100).toFixed(1)}%
      </text>
    </svg>
  )
}

function Sparkline({ data, width = 200, height = 40 }: { data: number[]; width?: number; height?: number }) {
  if (!data.length) return <div className="text-[9px] text-gray-700 italic">No buckets yet</div>
  const max = Math.max(...data, 0.01)
  const min = Math.min(...data, 0)
  const range = max - min || 0.01
  const points = data.map((v, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * width
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')

  // Threshold lines
  const thresholds = [
    { val: 0.55, color: '#EAB308', label: '55' },
    { val: 0.70, color: '#F97316', label: '70' },
    { val: 0.85, color: '#EF4444', label: '85' },
  ]

  return (
    <svg width={width} height={height} className="overflow-visible">
      {thresholds.map(t => {
        const y = height - ((t.val - min) / range) * (height - 4) - 2
        return y > 0 && y < height ? (
          <line key={t.label} x1={0} y1={y} x2={width} y2={y} stroke={t.color} strokeWidth={0.5} strokeDasharray="3,3" opacity={0.4} />
        ) : null
      })}
      <polyline points={points} fill="none" stroke="#0A84FF" strokeWidth={1.5} strokeLinejoin="round" />
      {/* Last point dot */}
      {data.length > 0 && (() => {
        const last = data[data.length - 1]
        const x = width
        const y = height - ((last - min) / range) * (height - 4) - 2
        const color = last >= 0.85 ? '#EF4444' : last >= 0.70 ? '#F97316' : last >= 0.55 ? '#EAB308' : '#0A84FF'
        return <circle cx={x} cy={y} r={3} fill={color} />
      })()}
    </svg>
  )
}

function BuySellBar({ buy, sell }: { buy: number; sell: number }) {
  const total = buy + sell || 1
  const buyPct = (buy / total) * 100
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[9px] font-mono">
        <span className="text-emerald-400">{buyPct.toFixed(0)}% BUY</span>
        <span className="text-red-400">{(100 - buyPct).toFixed(0)}% SELL</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
        <div className="bg-emerald-500 transition-all" style={{ width: `${buyPct}%` }} />
        <div className="bg-red-500 flex-1" />
      </div>
    </div>
  )
}

function InstrumentCard({ inst, onClick }: { inst: any; onClick: () => void }) {
  const sig = SIGNAL_COLORS[inst.signal] || SIGNAL_COLORS.NEUTRAL
  return (
    <div onClick={onClick} className={`border ${sig.border} ${sig.bg} rounded-xl p-4 cursor-pointer hover:brightness-110 transition-all`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-bold text-white tracking-wider">{inst.name}</span>
        <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold border ${sig.bg} ${sig.text} ${sig.border}`}>{inst.signal}</span>
      </div>

      {/* Gauge */}
      <div className="flex justify-center mb-2">
        <VPINGauge value={inst.vpin} size={100} />
      </div>

      {/* Buy/Sell Bar */}
      <BuySellBar buy={inst.buy_volume} sell={inst.sell_volume} />

      {/* Sparkline */}
      <div className="mt-3">
        <p className="text-[8px] text-gray-600 mb-1">Last {inst.sparkline?.length || 0} buckets</p>
        <Sparkline data={inst.sparkline || []} width={180} height={35} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mt-3 text-[9px] font-mono">
        <div><span className="text-gray-600">Buckets</span><br /><span className="text-white">{inst.buckets_completed}</span></div>
        <div><span className="text-gray-600">Ticks</span><br /><span className="text-white">{(inst.total_ticks || 0).toLocaleString('en-IN')}</span></div>
        <div><span className="text-gray-600">σ</span><br /><span className="text-white">{inst.sigma?.toFixed(4) || '—'}</span></div>
      </div>

      {/* Bucket progress */}
      <div className="mt-2">
        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500/50 transition-all" style={{ width: `${(inst.bucket_progress || 0) * 100}%` }} />
        </div>
        <p className="text-[8px] text-gray-700 mt-0.5">Bucket: {((inst.bucket_progress || 0) * 100).toFixed(0)}% filled</p>
      </div>
    </div>
  )
}

function DetailPanel({ inst, history, onClose }: { inst: any; history: any[]; onClose: () => void }) {
  const sig = SIGNAL_COLORS[inst.signal] || SIGNAL_COLORS.NEUTRAL
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#0a0a0a] border border-gray-800 rounded-2xl w-full max-w-3xl max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className={`border-b ${sig.border} px-5 py-3 flex items-center justify-between`}>
          <div>
            <h2 className="text-sm font-bold text-white">{inst.name} — VPIN Detail</h2>
            <p className={`text-[10px] ${sig.text}`}>{SIGNAL_ADVICE[inst.signal] || ''}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-2xl font-black font-mono ${sig.text}`}>{(inst.vpin * 100).toFixed(1)}%</span>
            <button onClick={onClose} className="text-gray-500 hover:text-white text-lg">✕</button>
          </div>
        </div>

        {/* Interpretation */}
        <div className="px-5 py-3 border-b border-gray-800 text-[11px] text-gray-400 leading-relaxed">
          <p className="font-bold text-gray-300 mb-1">What is VPIN?</p>
          <p>Volume-Synchronized Probability of Informed Trading measures the toxicity of order flow.
             High VPIN means informed traders (institutions) are active — adverse selection risk increases.
             As a <span className="text-emerald-400 font-bold">buyer</span>, use Nifty Futures VPIN as a leading indicator.
             When VPIN rises on futures, options premiums will follow with a lag — enter CE/PE before the move.</p>
        </div>

        {/* Bucket History */}
        <div className="px-5 py-3 overflow-y-auto max-h-[45vh]">
          <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-2 font-bold">Bucket History (Last {history.length})</p>
          <table className="w-full text-[10px] font-mono">
            <thead className="text-gray-600 border-b border-gray-800">
              <tr>
                <th className="text-left py-1.5">Time</th>
                <th className="text-right">Buy Vol</th>
                <th className="text-right">Sell Vol</th>
                <th className="text-right">VWAP</th>
                <th className="text-right">Imbalance</th>
                <th className="text-right">OI</th>
                <th className="text-right">Trades</th>
              </tr>
            </thead>
            <tbody>
              {[...history].reverse().map((b, i) => {
                const imbPct = (b.imbalance * 100)
                const imbColor = imbPct >= 85 ? 'text-red-400' : imbPct >= 70 ? 'text-orange-400' : imbPct >= 55 ? 'text-yellow-400' : 'text-blue-400'
                return (
                  <tr key={i} className="border-b border-gray-900/50 hover:bg-gray-900/30">
                    <td className="py-1.5 text-gray-400">{b.start_time}→{b.end_time}</td>
                    <td className="text-right text-emerald-400">{b.buy_volume.toLocaleString('en-IN')}</td>
                    <td className="text-right text-red-400">{b.sell_volume.toLocaleString('en-IN')}</td>
                    <td className="text-right text-white">{b.vwap.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td className={`text-right font-bold ${imbColor}`}>{imbPct.toFixed(1)}%</td>
                    <td className="text-right text-gray-500">{b.oi ? b.oi.toLocaleString('en-IN') : '—'}</td>
                    <td className="text-right text-gray-500">{b.trades}</td>
                  </tr>
                )
              })}
              {history.length === 0 && (
                <tr><td colSpan={7} className="text-center py-4 text-gray-700 italic">No buckets completed yet — waiting for volume</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function VPINDashboard({ state }: { state: any }) {
  const [selectedToken, setSelectedToken] = useState<string | null>(null)
  const vpin = (state as any).vpin || { instruments: {}, market_vpin: 0, market_signal: 'NEUTRAL' }
  const instruments = vpin.instruments || {}
  const entries = Object.entries(instruments) as [string, any][]

  const marketSig = SIGNAL_COLORS[vpin.market_signal] || SIGNAL_COLORS.NEUTRAL

  // Selected instrument detail
  const selectedInst = selectedToken ? instruments[selectedToken] : null
  const selectedHistory = selectedInst ? (selectedInst.sparkline || []).map((_: any, i: number) => {
    // We have sparkline data but not full bucket history in WebSocket state
    // For full history, would need API call — using sparkline as proxy
    return { start_time: '', end_time: '', buy_volume: 0, sell_volume: 0, vwap: 0, imbalance: _ as number, oi: 0, trades: 0 }
  }) : []

  return (
    <div className="h-full flex flex-col bg-[#080808] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-[#0a0f14] border-b border-blue-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center text-[10px] font-black text-black">VP</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.15em] text-[#0A84FF]">VPIN — FLOW TOXICITY</h1>
              <p className="text-[9px] text-blue-800">Futures VPIN = Leading Indicator → Options = Trade Vehicle</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* Market-wide signal */}
            <div className={`border ${marketSig.border} ${marketSig.bg} rounded-xl px-4 py-2 text-center`}>
              <p className="text-[8px] text-gray-500 uppercase tracking-widest">Market Toxicity</p>
              <p className={`text-xl font-black font-mono ${marketSig.text}`}>{(vpin.market_vpin * 100).toFixed(1)}%</p>
              <p className={`text-[9px] font-bold ${marketSig.text}`}>{vpin.market_signal}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* Trading Signal Panel */}
        <div className={`border ${marketSig.border} ${marketSig.bg} rounded-xl p-4`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`text-sm font-black ${marketSig.text}`}>
              {vpin.market_signal === 'EXTREME' ? '🚨' : vpin.market_signal === 'HIGH' ? '⚠️' : vpin.market_signal === 'ELEVATED' ? '👁' : '✓'} {vpin.market_signal}
            </span>
          </div>
          <p className={`text-[11px] ${marketSig.text} leading-relaxed`}>{vpin.market_advice || SIGNAL_ADVICE[vpin.market_signal] || ''}</p>

          {/* Signal levels reference */}
          <div className="grid grid-cols-4 gap-2 mt-3">
            {[
              { signal: 'NEUTRAL', range: '<55%', desc: 'Normal' },
              { signal: 'ELEVATED', range: '55-70%', desc: 'Watch' },
              { signal: 'HIGH', range: '70-85%', desc: 'Reduce' },
              { signal: 'EXTREME', range: '>85%', desc: 'Hedge' },
            ].map(s => {
              const c = SIGNAL_COLORS[s.signal]
              const isActive = vpin.market_signal === s.signal
              return (
                <div key={s.signal} className={`text-center rounded-lg p-2 border ${isActive ? c.border + ' ' + c.bg : 'border-gray-800 bg-gray-900/30'}`}>
                  <p className={`text-[10px] font-bold ${isActive ? c.text : 'text-gray-600'}`}>{s.signal}</p>
                  <p className="text-[9px] text-gray-600 font-mono">{s.range}</p>
                  <p className="text-[8px] text-gray-700">{s.desc}</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Instrument Cards */}
        {entries.length > 0 ? (
          <div className="grid grid-cols-3 gap-3">
            {entries.map(([token, inst]) => (
              <InstrumentCard key={token} inst={inst} onClick={() => setSelectedToken(token)} />
            ))}
          </div>
        ) : (
          <div className="border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-500 text-sm">Waiting for tick data...</p>
            <p className="text-[10px] text-gray-700 mt-1">VPIN activates when Kite WebSocket starts sending ticks during market hours.</p>
            <p className="text-[10px] text-gray-700">Registered: NIFTY-FUT (bucket=30K). ATM CE/PE register after first option chain build.</p>
          </div>
        )}

        {/* How to use — buyer focused */}
        <div className="border border-blue-900/20 bg-blue-950/10 rounded-xl p-4">
          <p className="text-[9px] text-blue-400 uppercase tracking-widest mb-2 font-bold">How to Use (Option Buyer)</p>
          <div className="grid grid-cols-2 gap-3 text-[10px] text-gray-400">
            <div>
              <p className="text-blue-400 font-bold mb-1">Futures VPIN = Leading Signal</p>
              <p>Nifty Futures order flow shows institutional intent BEFORE options react. VPIN spike on futures = option premiums will follow.</p>
            </div>
            <div>
              <p className="text-emerald-400 font-bold mb-1">Options = Trade Vehicle</p>
              <p>When futures VPIN goes ELEVATED/HIGH → buy ATM CE/PE before the move. Futures lead, options lag. Use the lag as your edge.</p>
            </div>
            <div>
              <p className="text-red-400 font-bold mb-1">EXTREME = Exit / Hedge</p>
              <p>VPIN &gt;85% means heavy informed flow. If you're already long, trail SL or hedge. Don't enter new positions.</p>
            </div>
            <div>
              <p className="text-yellow-400 font-bold mb-1">NEUTRAL = Safe Zone</p>
              <p>VPIN &lt;55% = normal market. Use other detectors (Bob tab) for entry signals. VPIN is your risk overlay.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedInst && (
        <DetailPanel inst={selectedInst} history={selectedHistory} onClose={() => setSelectedToken(null)} />
      )}
    </div>
  )
}
