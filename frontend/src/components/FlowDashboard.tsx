import { useState } from 'react'
import type { TradeState, DetectorResult, FlowEntry } from '../hooks/useWebSocket'

interface Props { state: TradeState; onBack: () => void }

const STR_CLR: Record<string, string> = { EXTREME: 'bg-red-500/25 text-red-400 border border-red-500/40', AGGRESSIVE: 'bg-neon-red/20 text-neon-red', STRONG: 'bg-neon-green/20 text-neon-green', MILD: 'bg-neon-yellow/20 text-neon-yellow' }

/** Extract CE/PE side from entry */
function getSide(f: FlowEntry): string {
  if (f.side) return f.side
  if (f.strike.includes('CE')) return 'CE'
  if (f.strike.includes('PE')) return 'PE'
  return ''
}

/** Flow Quadrant component — clean, no IV, focused on strike + price + volume + OI */
function FlowQuadrant({ title, subtitle, color, entries }: { title: string; subtitle: string; color: 'green' | 'red'; entries: FlowEntry[] }) {
  const borderClr = color === 'green' ? 'border-green-800/30' : 'border-red-800/30'
  const bgClr = color === 'green' ? 'bg-emerald-950/10' : 'bg-red-950/10'
  const titleClr = color === 'green' ? 'text-green-400' : 'text-red-400'
  // Aggregate by strike — show unique strikes with total volume
  const strikeAgg: Record<string, { vol: number; oi: number; price: number; count: number; time: string }> = {}
  entries.forEach(f => {
    const st = f.strike
    if (!strikeAgg[st]) strikeAgg[st] = { vol: 0, oi: 0, price: f.price, count: 0, time: f.time }
    strikeAgg[st].vol += f.volume
    strikeAgg[st].oi = Math.max(strikeAgg[st].oi, f.oi)
    strikeAgg[st].price = f.price
    strikeAgg[st].count++
    strikeAgg[st].time = f.time
  })
  const sorted = Object.entries(strikeAgg).sort((a, b) => b[1].vol - a[1].vol)
  const maxVol = sorted[0]?.[1]?.vol || 1

  return (
    <div className={`${bgClr} flex flex-col overflow-hidden`}>
      <div className={`flex items-center justify-between px-3 py-1.5 border-b ${borderClr} shrink-0`}>
        <div className="flex items-center gap-2">
          <span className={`text-[12px] font-extrabold ${titleClr}`}>{title}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${color === 'green' ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'}`}>{subtitle}</span>
        </div>
        <span className={`text-[11px] font-mono font-extrabold ${titleClr}`}>{sorted.length} strikes</span>
      </div>
      {/* Column headers */}
      <div className="flex items-center px-3 py-1 text-[9px] text-gray-500 font-bold uppercase border-b border-gray-800/50 shrink-0">
        <span className="w-20">Strike</span>
        <span className="w-16 text-right">Price</span>
        <span className="flex-1 text-center">Volume</span>
        <span className="w-20 text-right">OI</span>
      </div>
      <div className="flex-1 overflow-y-auto font-mono">
        {sorted.length === 0 && <p className="text-gray-600 text-center py-6 text-[12px]">No activity yet</p>}
        {sorted.map(([strike, data], i) => (
          <div key={strike} className={`flex items-center px-3 py-1.5 border-b ${borderClr} hover:bg-white/[0.03] ${i === 0 ? 'bg-white/[0.02]' : ''}`}>
            <span className={`w-20 font-extrabold text-[13px] ${titleClr}`}>{strike}</span>
            <span className="w-16 text-right text-white font-bold text-[12px]">₹{data.price.toFixed(1)}</span>
            <div className="flex-1 flex items-center gap-2 px-2">
              <div className="flex-1 h-3 bg-gray-800/60 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all ${color === 'green' ? 'bg-green-500/70' : 'bg-red-500/70'}`}
                  style={{ width: `${Math.min(100, (data.vol / maxVol) * 100)}%` }} />
              </div>
              <span className={`text-[11px] font-bold min-w-[60px] text-right ${data.vol > 50000 ? 'text-yellow-400' : 'text-gray-300'}`}>
                {data.vol > 1e5 ? `${(data.vol / 1e5).toFixed(1)}L` : data.vol.toLocaleString()}
              </span>
            </div>
            <span className="w-20 text-right text-gray-400 text-[11px]">{data.oi > 1e5 ? `${(data.oi / 1e5).toFixed(1)}L` : data.oi.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Parse ISO or time string to HH:MM:SS in IST */
function fmtTime(t: string): string {
  if (!t) return '--:--:--'
  try {
    // If it's just HH:MM:SS already
    if (/^\d{2}:\d{2}:\d{2}$/.test(t)) return t
    // Parse ISO — add IST offset if no timezone specified
    const d = new Date(t.includes('+') || t.includes('Z') ? t : t + '+05:30')
    const h = d.getHours().toString().padStart(2, '0')
    const m = d.getMinutes().toString().padStart(2, '0')
    const s = d.getSeconds().toString().padStart(2, '0')
    return `${h}:${m}:${s}`
  } catch { return '--:--:--' }
}

function fmtTimeShort(t: string): string {
  const full = fmtTime(t)
  return full.slice(0, 5) // HH:MM
}

export default function FlowDashboard({ state, onBack }: Props) {
  const { brain, confluence, flow_tape: tape, signal_history, detectors, ai_analysis, spot, atm, india_vix, fii_dii } = state
  const [expandedDet, setExpandedDet] = useState<string | null>(null)
  const [showAI, setShowAI] = useState(false)

  const sig = brain.active && brain.primary ? brain : null
  const allTape = [...(tape || [])]
  const detList = Object.values(detectors || {}).sort((a, b) => b.score - a.score)
  const history = signal_history ? [...signal_history].reverse().slice(0, 20) : []

  const vixLabel = india_vix ? (india_vix > 20 ? 'FEAR' : india_vix > 14 ? 'CAUTION' : 'GREED') : null
  const vixClr = india_vix ? (india_vix > 20 ? 'text-red-400' : india_vix > 14 ? 'text-yellow-400' : 'text-green-400') : ''
  const dirClr = confluence.direction === 'BULLISH' ? 'text-green-400' : confluence.direction === 'BEARISH' ? 'text-red-400' : 'text-gray-300'

  return (
    <div className="h-screen flex flex-col bg-tb-bg overflow-hidden">
      {/* SECTION 1: LIVE TRADE SIGNAL — top banner */}
      <div className={`shrink-0 border-b ${sig ? 'border-green-500/40 bg-emerald-950/15' : 'border-tb-border bg-tb-card/30'}`}>
        <div className="flex items-center justify-between px-5 py-2">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="text-cyan-400 hover:text-cyan-300 text-sm font-bold">← Main</button>
            <span className="text-gray-600">|</span>
            <h1 className="text-sm font-extrabold tracking-widest text-purple-400 uppercase">Flow Dashboard</h1>
          </div>
          <div className="flex items-center gap-5 text-xs font-mono">
            <span className="text-gray-400">SPOT <span className="text-white font-bold text-sm">{spot.toLocaleString('en-IN')}</span></span>
            <span className="text-gray-400">ATM <span className="text-cyan-400 font-bold text-sm">{atm}</span></span>
          </div>
        </div>
        <div className="px-5 pb-2.5">
          {sig && sig.primary ? (
            <div className="flex items-center gap-6 flex-wrap">
              <div className="flex items-center gap-3">
                <span className={`text-2xl font-black ${sig.direction === 'BULLISH' ? 'text-green-400' : 'text-red-400'}`}>
                  {sig.primary.action} {sig.primary.strike}
                </span>
                {sig.strength && <span className={`text-[10px] px-2.5 py-1 rounded-lg font-extrabold ${STR_CLR[sig.strength] || 'bg-tb-surface text-gray-400'}`}>{sig.strength}</span>}
              </div>
              <div className="flex items-center gap-5 text-xs font-mono">
                <span className="text-gray-300">CMP <span className="text-white font-bold">{sig.primary.cmp}</span></span>
                <span className="text-gray-300">T1 <span className="text-green-400 font-bold">{sig.primary.target1}</span></span>
                <span className="text-gray-300">T2 <span className="text-green-400 font-bold">{sig.primary.target2}</span></span>
                <span className="text-gray-300">SL <span className="text-red-400 font-bold">{sig.primary.stop_loss}</span></span>
                <span className="text-gray-300">TL <span className="text-yellow-400">{sig.primary.time_limit}</span></span>
              </div>
              {sig.secondary && (
                <span className="text-xs font-mono text-orange-400 font-bold">ALT: {sig.secondary.action} {sig.secondary.strike} @ {sig.secondary.cmp}</span>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-xs font-mono">Monitoring... No active signal — Score: {confluence.score.toFixed(0)}/100</p>
          )}
        </div>
      </div>

      {/* HOT STRIKES + TRADE CONCLUSION — middle insight bar */}
      <div className="shrink-0 grid grid-cols-2 gap-[1px] bg-tb-border border-b border-tb-border" style={{ maxHeight: '200px' }}>
        {/* 🔥 HOT STRIKES — clean table layout */}
        <div className="bg-gray-900/80 p-3 overflow-y-auto">
          <h2 className="text-[11px] font-extrabold text-orange-400 uppercase tracking-widest mb-2">🔥 Hot Strikes — Heaviest Selling</h2>
          {(() => {
            const strikeMap: Record<string, { ce_sell: number; pe_sell: number; ce_buy: number; pe_buy: number; total_vol: number }> = {}
            allTape.forEach(f => {
              const stNum = f.strike.replace(/\s*(CE|PE)/, '').trim()
              const side = getSide(f)
              if (!strikeMap[stNum]) strikeMap[stNum] = { ce_sell: 0, pe_sell: 0, ce_buy: 0, pe_buy: 0, total_vol: 0 }
              strikeMap[stNum].total_vol += f.volume
              if (side === 'CE' && f.type === 'SELL') strikeMap[stNum].ce_sell += f.volume
              if (side === 'PE' && f.type === 'SELL') strikeMap[stNum].pe_sell += f.volume
              if (side === 'CE' && f.type === 'BUY') strikeMap[stNum].ce_buy += f.volume
              if (side === 'PE' && f.type === 'BUY') strikeMap[stNum].pe_buy += f.volume
            })
            const maxPeSell = Object.entries(strikeMap).filter(([, d]) => d.pe_sell > 0).sort((a, b) => b[1].pe_sell - a[1].pe_sell).slice(0, 4)
            const maxCeSell = Object.entries(strikeMap).filter(([, d]) => d.ce_sell > 0).sort((a, b) => b[1].ce_sell - a[1].ce_sell).slice(0, 4)
            const peMax = maxPeSell[0]?.[1]?.pe_sell || 1
            const ceMax = maxCeSell[0]?.[1]?.ce_sell || 1
            return (
              <div className="grid grid-cols-2 gap-4">
                {/* PUT SELLING = Support */}
                <div>
                  <p className="text-[10px] text-green-400 font-bold mb-2">📈 PUT SELLING <span className="text-gray-500 font-normal">(Support)</span></p>
                  <table className="w-full text-[11px] font-mono">
                    <thead><tr className="text-[9px] text-gray-500 uppercase">
                      <th className="text-left pb-1 w-16">Strike</th>
                      <th className="text-left pb-1">Bar</th>
                      <th className="text-right pb-1 w-16">Volume</th>
                    </tr></thead>
                    <tbody>
                      {maxPeSell.length === 0 && <tr><td colSpan={3} className="text-gray-600 py-2">No PE selling</td></tr>}
                      {maxPeSell.map(([strike, data]) => (
                        <tr key={strike} className="border-t border-gray-800/30">
                          <td className="text-green-400 font-extrabold text-[13px] py-1">{strike}</td>
                          <td className="py-1 px-1"><div className="h-2.5 bg-gray-800 rounded-full overflow-hidden"><div className="h-full bg-green-500/70 rounded-full" style={{ width: `${(data.pe_sell / peMax) * 100}%` }} /></div></td>
                          <td className="text-green-400 font-bold text-right py-1">{data.pe_sell > 1e5 ? `${(data.pe_sell / 1e5).toFixed(1)}L` : data.pe_sell.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* CALL SELLING = Resistance */}
                <div>
                  <p className="text-[10px] text-red-400 font-bold mb-2">📉 CALL SELLING <span className="text-gray-500 font-normal">(Resistance)</span></p>
                  <table className="w-full text-[11px] font-mono">
                    <thead><tr className="text-[9px] text-gray-500 uppercase">
                      <th className="text-left pb-1 w-16">Strike</th>
                      <th className="text-left pb-1">Bar</th>
                      <th className="text-right pb-1 w-16">Volume</th>
                    </tr></thead>
                    <tbody>
                      {maxCeSell.length === 0 && <tr><td colSpan={3} className="text-gray-600 py-2">No CE selling</td></tr>}
                      {maxCeSell.map(([strike, data]) => (
                        <tr key={strike} className="border-t border-gray-800/30">
                          <td className="text-red-400 font-extrabold text-[13px] py-1">{strike}</td>
                          <td className="py-1 px-1"><div className="h-2.5 bg-gray-800 rounded-full overflow-hidden"><div className="h-full bg-red-500/70 rounded-full" style={{ width: `${(data.ce_sell / ceMax) * 100}%` }} /></div></td>
                          <td className="text-red-400 font-bold text-right py-1">{data.ce_sell > 1e5 ? `${(data.ce_sell / 1e5).toFixed(1)}L` : data.ce_sell.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })()}
        </div>

        {/* 💡 TRADE CONCLUSION + ZONE ANALYSIS */}
        <div className="bg-gray-900/80 p-3 overflow-y-auto">
          <h2 className="text-[11px] font-extrabold text-yellow-400 uppercase tracking-widest mb-2">💡 Trade Conclusion + Zone Map</h2>
          {(() => {
            const dir = confluence.direction
            const score = confluence.score
            const bull = dir === 'BULLISH'
            const bear = dir === 'BEARISH'
            const primary = brain.primary
            const strength = brain.strength || (score >= 80 ? 'EXTREME' : score >= 60 ? 'STRONG' : score >= 40 ? 'MILD' : 'WEAK')
            const za = (state as any).zone_analysis || {}
            const support = za.support_zone || atm - 100
            const resistance = za.resistance_zone || atm + 100
            const winner = za.winner || 'NEUTRAL'
            const reversal = za.reversal_zone || atm
            const traps = za.trap_zones || []
            const buyersScore = za.buyers_score || 0
            const sellersScore = za.sellers_score || 0
            const totalScore = buyersScore + sellersScore || 1
            const buyersPct = Math.round((buyersScore / totalScore) * 100)

            return (
              <div className="space-y-2">
                {/* Trade signal */}
                <div className={`rounded-xl border p-2.5 ${bull ? 'border-green-600/50 bg-emerald-950/30' : bear ? 'border-red-600/50 bg-red-950/30' : 'border-gray-600 bg-gray-800/30'}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-black ${bull ? 'text-green-400' : bear ? 'text-red-400' : 'text-gray-300'}`}>
                        {bull ? '🟢 BUY CALL' : bear ? '🔴 BUY PUT' : '⚪ WAIT'}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-extrabold ${STR_CLR[strength] || 'bg-gray-700 text-gray-400'}`}>{strength}</span>
                    </div>
                    <span className={`text-lg font-black font-mono ${bull ? 'text-green-400' : bear ? 'text-red-400' : 'text-gray-400'}`}>{score.toFixed(0)}%</span>
                  </div>
                  {primary ? (
                    <div className="grid grid-cols-5 gap-1 text-center text-[11px]">
                      {[
                        { label: 'STRIKE', val: primary.strike, clr: 'text-white' },
                        { label: 'ENTRY', val: primary.cmp, clr: 'text-cyan-400' },
                        { label: 'TARGET', val: primary.target1, clr: 'text-green-400' },
                        { label: 'SL', val: primary.stop_loss, clr: 'text-red-400' },
                        { label: 'TIME', val: primary.time_limit, clr: 'text-yellow-400' },
                      ].map(x => (
                        <div key={x.label} className="bg-black/20 rounded-lg p-1.5">
                          <span className="text-gray-500 text-[8px] block font-bold">{x.label}</span>
                          <span className={`${x.clr} font-extrabold text-[13px]`}>{x.val}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-[11px] font-mono">Signal building... {dir} bias at {score.toFixed(0)}%</p>
                  )}
                </div>

                {/* Zone Map — 2x3 grid */}
                <div className="grid grid-cols-3 gap-1.5 text-[11px] font-mono">
                  <div className="bg-green-950/20 border border-green-800/30 rounded-lg p-1.5 text-center">
                    <span className="text-gray-500 text-[8px] block font-bold">SUPPORT</span>
                    <span className="text-green-400 font-extrabold text-[15px]">{support}</span>
                    <span className="text-green-600 text-[8px] block">PE Sellers Here</span>
                  </div>
                  <div className="bg-red-950/20 border border-red-800/30 rounded-lg p-1.5 text-center">
                    <span className="text-gray-500 text-[8px] block font-bold">RESISTANCE</span>
                    <span className="text-red-400 font-extrabold text-[15px]">{resistance}</span>
                    <span className="text-red-600 text-[8px] block">CE Sellers Here</span>
                  </div>
                  <div className="bg-purple-950/20 border border-purple-800/30 rounded-lg p-1.5 text-center">
                    <span className="text-gray-500 text-[8px] block font-bold">REVERSAL</span>
                    <span className="text-purple-400 font-extrabold text-[15px]">{reversal}</span>
                    <span className="text-purple-600 text-[8px] block">Max OI Both Sides</span>
                  </div>
                </div>

                {/* Buyers vs Sellers bar */}
                <div className="bg-gray-800/30 border border-gray-700/30 rounded-lg p-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-green-400 text-[10px] font-bold">BUYERS {buyersPct}%</span>
                    <span className={`text-[11px] font-extrabold px-2 py-0.5 rounded ${winner === 'BUYERS' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                      {winner} WINNING
                    </span>
                    <span className="text-red-400 text-[10px] font-bold">SELLERS {100 - buyersPct}%</span>
                  </div>
                  <div className="h-3 bg-gray-700 rounded-full overflow-hidden flex">
                    <div className="bg-green-500/70 h-full transition-all" style={{ width: `${buyersPct}%` }} />
                    <div className="bg-red-500/70 h-full transition-all" style={{ width: `${100 - buyersPct}%` }} />
                  </div>
                </div>

                {/* Trap zones */}
                {traps.length > 0 && (
                  <div className="bg-yellow-950/15 border border-yellow-800/30 rounded-lg p-2">
                    <span className="text-yellow-400 text-[10px] font-extrabold">⚠️ TRAP ZONES</span>
                    <span className="text-gray-400 text-[9px] ml-2">(Both sides building OI — potential trap)</span>
                    <div className="flex gap-2 mt-1">
                      {traps.map((t: any, i: number) => (
                        <span key={i} className="text-yellow-400 text-[12px] font-bold bg-yellow-900/30 px-2 py-0.5 rounded">{t.strike}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      </div>

      {/* MAIN 3-COL GRID */}
      <div className="flex-1 grid grid-cols-[280px_1fr_340px] gap-[1px] bg-tb-border overflow-hidden">

        {/* SECTION 2: SIGNAL HISTORY — left column */}
        <div className="bg-tb-bg p-3 flex flex-col overflow-hidden">
          <h2 className="text-xs font-extrabold text-green-400 uppercase tracking-widest mb-2 shrink-0">📡 Signal History ({history.length})</h2>
          <div className="flex-1 overflow-y-auto space-y-2">
            {history.length === 0 && <p className="text-gray-500 text-center py-8 text-sm">No signals recorded yet</p>}
            {history.map((s, i) => {
              const bull = s.direction === 'BULLISH'
              const pnl = s.spot_at_signal && spot ? ((spot - s.spot_at_signal) * (bull ? 1 : -1)).toFixed(1) : null
              return (
                <div key={i} className={`rounded-xl p-3 border ${bull ? 'border-green-700/40 bg-emerald-950/20' : 'border-red-700/40 bg-red-950/20'}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-black ${bull ? 'text-green-400' : 'text-red-400'}`}>{bull ? '▲' : '▼'}</span>
                      <span className="text-white font-bold text-sm">{s.primary?.strike || '—'}</span>
                      <span className="text-gray-400 text-[10px] font-mono">{(s.index || '').slice(0, 3)}</span>
                    </div>
                    <span className="text-gray-400 text-[11px] font-mono">{fmtTimeShort(s.recorded_at || '')}</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-[11px] font-mono">
                    <div>
                      <span className="text-gray-500 text-[9px] block">ENTRY</span>
                      <span className="text-white font-bold">{s.primary?.cmp || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-[9px] block">TARGET</span>
                      <span className="text-green-400 font-bold">{s.primary?.target1 || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-[9px] block">SL</span>
                      <span className="text-red-400 font-bold">{s.primary?.stop_loss || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 text-[9px] block">SPOT</span>
                      <span className="text-gray-300">{s.spot_at_signal?.toLocaleString('en-IN') || '—'}</span>
                    </div>
                  </div>
                  {pnl && (
                    <div className={`mt-1.5 pt-1.5 border-t border-gray-800 text-[10px] font-mono ${Number(pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      NIFTY Move: {Number(pnl) >= 0 ? '+' : ''}{pnl} pts since signal
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* SECTION 3: 4-QUADRANT FLOW TAPE — center */}
        <div className="bg-tb-bg flex flex-col overflow-hidden">
          {/* Quadrant header */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700 shrink-0">
            <h2 className="text-xs font-extrabold text-purple-400 uppercase tracking-widest">Options Flow — 4 Quadrant</h2>
            <div className="flex items-center gap-3 text-[10px] font-mono font-bold">
              <span className="text-green-400">CE BUY {allTape.filter(t => getSide(t) === 'CE' && t.type === 'BUY').length}</span>
              <span className="text-red-400">CE SELL {allTape.filter(t => getSide(t) === 'CE' && t.type === 'SELL').length}</span>
              <span className="text-gray-400">|</span>
              <span className="text-red-400">PE BUY {allTape.filter(t => getSide(t) === 'PE' && t.type === 'BUY').length}</span>
              <span className="text-green-400">PE SELL {allTape.filter(t => getSide(t) === 'PE' && t.type === 'SELL').length}</span>
            </div>
          </div>
          {/* 2x2 Grid */}
          <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-[1px] bg-gray-700 overflow-hidden">
            {/* CE BUYING — Bullish */}
            <FlowQuadrant
              title="📈 CALL BUYING" subtitle="Bullish" color="green"
              entries={allTape.filter(t => getSide(t) === 'CE' && t.type === 'BUY').reverse().slice(0, 25)}
            />
            {/* PE BUYING — Bearish */}
            <FlowQuadrant
              title="📉 PUT BUYING" subtitle="Bearish" color="red"
              entries={allTape.filter(t => getSide(t) === 'PE' && t.type === 'BUY').reverse().slice(0, 25)}
            />
            {/* CE SELLING — Bearish */}
            <FlowQuadrant
              title="📉 CALL SELLING" subtitle="Bearish" color="red"
              entries={allTape.filter(t => getSide(t) === 'CE' && t.type === 'SELL').reverse().slice(0, 25)}
            />
            {/* PE SELLING — Bullish */}
            <FlowQuadrant
              title="📈 PUT SELLING" subtitle="Bullish" color="green"
              entries={allTape.filter(t => getSide(t) === 'PE' && t.type === 'SELL').reverse().slice(0, 25)}
            />
          </div>
        </div>

        {/* SECTION 4: DETECTOR BREAKDOWN — right column */}
        <div className="bg-tb-bg p-3 flex flex-col overflow-hidden">
          <h2 className="text-xs font-extrabold text-cyan-400 uppercase tracking-widest mb-2 shrink-0">Detectors ({detList.length})</h2>
          <div className="flex-1 overflow-y-auto space-y-1.5">
            {detList.map((d: DetectorResult) => (
              <div key={d.id} className={`border rounded-xl p-2.5 cursor-pointer transition-all ${
                d.status === 'CRITICAL' ? 'border-green-500/50 bg-emerald-950/20' :
                d.status === 'ALERT' ? 'border-green-600/30 bg-emerald-950/10' :
                d.status === 'WATCH' ? 'border-yellow-600/30 bg-yellow-950/10' :
                'border-gray-700/40 hover:bg-gray-900/30'
              }`} onClick={() => setExpandedDet(expandedDet === d.id ? null : d.id)}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[12px] font-bold ${d.score > 0 ? 'text-white' : 'text-gray-500'}`}>{d.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[12px] font-mono font-extrabold ${d.score >= 70 ? 'text-green-400' : d.score >= 30 ? 'text-yellow-400' : 'text-gray-600'}`}>{d.score}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-md font-extrabold ${
                      d.status === 'CRITICAL' ? 'bg-green-500/25 text-green-400' :
                      d.status === 'ALERT' ? 'bg-green-600/20 text-green-400' :
                      d.status === 'WATCH' ? 'bg-yellow-600/20 text-yellow-400' :
                      'bg-gray-800/50 text-gray-500'
                    }`}>{d.status}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${
                      d.status === 'CRITICAL' ? 'bg-green-500' :
                      d.status === 'ALERT' ? 'bg-green-600' :
                      d.status === 'WATCH' ? 'bg-yellow-500' :
                      'bg-gray-700'
                    }`} style={{ width: `${Math.min(d.score, 100)}%` }} />
                  </div>
                </div>
                <p className={`text-[11px] ${d.score > 0 ? 'text-gray-300' : 'text-gray-600'}`}>{d.metric}</p>
                {expandedDet === d.id && d.alerts && d.alerts.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-700/50 space-y-1">
                    {d.alerts.slice(0, 5).map((a: any, i: number) => (
                      <p key={i} className="text-[10px] text-yellow-400 font-mono">{typeof a === 'string' ? a : JSON.stringify(a)}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SECTION 5: MARKET CONTEXT — bottom bar */}
      <div className="shrink-0 flex items-center justify-between px-5 py-2 bg-gray-900/60 border-t border-gray-700 text-[11px] font-mono">
        <div className="flex items-center gap-5">
          {india_vix != null && (
            <span className="text-gray-300">VIX <span className={`font-bold ${vixClr}`}>{india_vix.toFixed(2)}</span> <span className={`text-[9px] font-bold ${vixClr}`}>{vixLabel}</span></span>
          )}
          {fii_dii && (
            <>
              <span className="text-gray-300">FII <span className={`font-bold ${(fii_dii.fii_net_cr || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{(fii_dii.fii_net_cr || 0) >= 0 ? '+' : ''}{fii_dii.fii_net_cr?.toFixed(0)}Cr</span></span>
              <span className="text-gray-300">DII <span className={`font-bold ${(fii_dii.dii_net_cr || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>{(fii_dii.dii_net_cr || 0) >= 0 ? '+' : ''}{fii_dii.dii_net_cr?.toFixed(0)}Cr</span></span>
            </>
          )}
        </div>
        <div className="flex items-center gap-5">
          <span className={`font-extrabold ${dirClr}`}>{confluence.direction} {confluence.score.toFixed(0)}/100</span>
          <span className="text-gray-300">IDX <span className="text-cyan-400 font-bold">{state.active_index || 'NIFTY'}</span></span>
          <span className="text-gray-300">SPOT <span className="text-white font-bold">{spot.toLocaleString('en-IN')}</span></span>
        </div>
        <button onClick={() => setShowAI(!showAI)} className={`text-[10px] px-3 py-1 rounded-lg font-bold transition-all ${showAI ? 'bg-purple-900/40 text-purple-400 border border-purple-600/40' : 'text-gray-400 hover:text-purple-400 border border-gray-700'}`}>
          {showAI ? 'Hide AI' : '🤖 AI Analysis'}
        </button>
      </div>

      {/* SECTION 6: AI ANALYSIS — expandable */}
      {showAI && ai_analysis && (
        <div className="shrink-0 max-h-56 overflow-y-auto bg-gray-900/70 border-t border-purple-600/30 px-5 py-3 space-y-2">
          <div className="flex items-center gap-3 mb-1.5">
            <h3 className="text-xs font-extrabold text-purple-400 uppercase tracking-widest">AI Analysis</h3>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-lg font-bold ${ai_analysis.sentiment === 'BULLISH' ? 'bg-green-900/40 text-green-400' : ai_analysis.sentiment === 'BEARISH' ? 'bg-red-900/40 text-red-400' : 'bg-gray-800 text-gray-300'}`}>{ai_analysis.sentiment}</span>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-lg font-bold ${ai_analysis.confidence === 'HIGH' ? 'bg-green-900/30 text-green-400' : ai_analysis.confidence === 'LOW' ? 'bg-red-900/30 text-red-400' : 'bg-yellow-900/30 text-yellow-400'}`}>{ai_analysis.confidence} conf</span>
          </div>
          <p className="text-xs text-gray-200 leading-relaxed">{ai_analysis.analysis || ai_analysis.summary}</p>
          {ai_analysis.bullets && ai_analysis.bullets.length > 0 && (
            <ul className="space-y-1">
              {ai_analysis.bullets.map((b, i) => <li key={i} className="text-[11px] text-gray-300 font-mono pl-3 border-l-2 border-cyan-600/40">{b}</li>)}
            </ul>
          )}
          {ai_analysis.risk_notes && ai_analysis.risk_notes.length > 0 && (
            <div className="pt-1.5 border-t border-gray-700/50">
              <p className="text-[10px] text-red-400 uppercase font-bold mb-1">⚠ Risk Notes</p>
              {ai_analysis.risk_notes.map((r, i) => <p key={i} className="text-[10px] text-red-300/90 font-mono">{r}</p>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
