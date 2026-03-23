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

/** Flow Quadrant component */
function FlowQuadrant({ title, subtitle, color, entries }: { title: string; subtitle: string; color: 'green' | 'red'; entries: FlowEntry[] }) {
  const borderClr = color === 'green' ? 'border-green-800/30' : 'border-red-800/30'
  const bgClr = color === 'green' ? 'bg-emerald-950/10' : 'bg-red-950/10'
  const titleClr = color === 'green' ? 'text-green-400' : 'text-red-400'
  return (
    <div className={`${bgClr} flex flex-col overflow-hidden`}>
      <div className={`flex items-center justify-between px-2 py-1.5 border-b ${borderClr} shrink-0`}>
        <div className="flex items-center gap-2">
          <span className={`text-[11px] font-extrabold ${titleClr}`}>{title}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${color === 'green' ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'}`}>{subtitle}</span>
        </div>
        <span className="text-gray-500 text-[10px] font-mono font-bold">{entries.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto font-mono text-[10px]">
        {entries.length === 0 && <p className="text-gray-600 text-center py-4 text-[11px]">No activity</p>}
        {entries.map((f, i) => (
          <div key={i} className={`flex items-center gap-2 px-2 py-[3px] border-b ${borderClr} hover:bg-white/[0.02]`}>
            <span className="text-gray-400 w-12">{fmtTime(f.time).slice(0, 5)}</span>
            <span className="text-white font-bold w-20">{f.strike}</span>
            <span className="text-white w-14 text-right font-semibold">₹{f.price.toFixed(1)}</span>
            <span className={`w-16 text-right ${f.volume > 5000 ? 'text-yellow-400 font-bold' : 'text-gray-300'}`}>{f.volume.toLocaleString()}</span>
            <span className="text-gray-400 w-16 text-right">{f.oi.toLocaleString()}</span>
            {f.buy_pct !== undefined && <span className={`w-10 text-right text-[9px] ${f.buy_pct > 55 ? 'text-green-400' : f.buy_pct < 45 ? 'text-red-400' : 'text-gray-500'}`}>{f.buy_pct}%</span>}
            {f.iv !== undefined && f.iv > 0 && <span className="w-10 text-right text-[9px] text-yellow-400">{f.iv.toFixed(0)}IV</span>}
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
      <div className="shrink-0 grid grid-cols-2 gap-[1px] bg-tb-border border-b border-tb-border" style={{ maxHeight: '180px' }}>
        {/* 🔥 HOT STRIKES — where max selling is happening */}
        <div className="bg-gray-900/80 p-3 overflow-y-auto">
          <h2 className="text-[11px] font-extrabold text-orange-400 uppercase tracking-widest mb-2">🔥 Hot Strikes — Heaviest Activity</h2>
          {(() => {
            // Aggregate flow tape by strike to find heaviest selling
            const strikeMap: Record<string, { ce_sell: number; pe_sell: number; ce_buy: number; pe_buy: number; total_vol: number; last_price: number }> = {}
            allTape.forEach(f => {
              const stNum = f.strike.replace(/\s*(CE|PE)/, '').trim()
              const side = getSide(f)
              if (!strikeMap[stNum]) strikeMap[stNum] = { ce_sell: 0, pe_sell: 0, ce_buy: 0, pe_buy: 0, total_vol: 0, last_price: 0 }
              strikeMap[stNum].total_vol += f.volume
              if (side === 'CE' && f.type === 'SELL') strikeMap[stNum].ce_sell += f.volume
              if (side === 'PE' && f.type === 'SELL') strikeMap[stNum].pe_sell += f.volume
              if (side === 'CE' && f.type === 'BUY') strikeMap[stNum].ce_buy += f.volume
              if (side === 'PE' && f.type === 'BUY') strikeMap[stNum].pe_buy += f.volume
            })
            // Also use chain_summary for OI data
            const chain = state.chain_summary || []
            chain.forEach(r => {
              const stNum = r.strike.toString()
              if (!strikeMap[stNum]) strikeMap[stNum] = { ce_sell: 0, pe_sell: 0, ce_buy: 0, pe_buy: 0, total_vol: 0, last_price: 0 }
            })
            const sorted = Object.entries(strikeMap)
              .map(([strike, data]) => ({ strike: Number(strike), ...data, sell_total: data.ce_sell + data.pe_sell }))
              .sort((a, b) => b.total_vol - a.total_vol)
              .slice(0, 6)
            const maxPeSell = Object.entries(strikeMap).sort((a, b) => b[1].pe_sell - a[1].pe_sell).slice(0, 3)
            const maxCeSell = Object.entries(strikeMap).sort((a, b) => b[1].ce_sell - a[1].ce_sell).slice(0, 3)
            return (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-3">
                  {/* Max PE Selling = Support = Bullish */}
                  <div>
                    <p className="text-[10px] text-green-400 font-bold mb-1.5">📈 MAX PUT SELLING <span className="text-gray-500">(Support/Bullish)</span></p>
                    {maxPeSell.filter(([, d]) => d.pe_sell > 0).length === 0 && <p className="text-gray-600 text-[10px]">No PE selling detected</p>}
                    {maxPeSell.filter(([, d]) => d.pe_sell > 0).map(([strike, data]) => (
                      <div key={strike} className="flex items-center gap-2 py-[2px]">
                        <span className="text-green-400 font-extrabold text-[13px] font-mono w-16">{strike}</span>
                        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.min(100, (data.pe_sell / (maxPeSell[0]?.[1]?.pe_sell || 1)) * 100)}%` }} />
                        </div>
                        <span className="text-green-400 text-[10px] font-mono font-bold w-16 text-right">{data.pe_sell.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                  {/* Max CE Selling = Resistance = Bearish */}
                  <div>
                    <p className="text-[10px] text-red-400 font-bold mb-1.5">📉 MAX CALL SELLING <span className="text-gray-500">(Resistance/Bearish)</span></p>
                    {maxCeSell.filter(([, d]) => d.ce_sell > 0).length === 0 && <p className="text-gray-600 text-[10px]">No CE selling detected</p>}
                    {maxCeSell.filter(([, d]) => d.ce_sell > 0).map(([strike, data]) => (
                      <div key={strike} className="flex items-center gap-2 py-[2px]">
                        <span className="text-red-400 font-extrabold text-[13px] font-mono w-16">{strike}</span>
                        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(100, (data.ce_sell / (maxCeSell[0]?.[1]?.ce_sell || 1)) * 100)}%` }} />
                        </div>
                        <span className="text-red-400 text-[10px] font-mono font-bold w-16 text-right">{data.ce_sell.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
                {/* Top Active Strikes */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[9px] text-gray-500 font-bold uppercase">Most Active:</span>
                  {sorted.slice(0, 5).map(s => (
                    <span key={s.strike} className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded ${s.strike === atm ? 'bg-cyan-900/40 text-cyan-400 border border-cyan-700/30' : 'bg-gray-800 text-gray-300'}`}>
                      {s.strike} <span className="text-gray-500">{s.total_vol.toLocaleString()}</span>
                    </span>
                  ))}
                </div>
              </div>
            )
          })()}
        </div>

        {/* 💡 TRADE CONCLUSION — simple setup for normal person */}
        <div className="bg-gray-900/80 p-3 overflow-y-auto">
          <h2 className="text-[11px] font-extrabold text-yellow-400 uppercase tracking-widest mb-2">💡 Trade Conclusion — What To Do</h2>
          {(() => {
            const dir = confluence.direction
            const score = confluence.score
            const bull = dir === 'BULLISH'
            const bear = dir === 'BEARISH'
            const primary = brain.primary
            const strength = brain.strength || (score >= 80 ? 'EXTREME' : score >= 60 ? 'STRONG' : score >= 40 ? 'MILD' : 'WEAK')
            // Find support/resistance from chain
            const chain = state.chain_summary || []
            const maxPeOI = chain.reduce((max, r) => r.pe_oi > (max?.pe_oi || 0) ? r : max, chain[0])
            const maxCeOI = chain.reduce((max, r) => r.ce_oi > (max?.ce_oi || 0) ? r : max, chain[0])
            const support = maxPeOI?.strike || atm - 100
            const resistance = maxCeOI?.strike || atm + 100

            if (score < 30) {
              return (
                <div className="space-y-2">
                  <div className="rounded-xl bg-gray-800/50 border border-gray-700 p-3 text-center">
                    <p className="text-gray-400 text-sm font-bold mb-1">⏸ NO CLEAR TRADE</p>
                    <p className="text-gray-500 text-[11px]">Confluence score {score.toFixed(0)}/100 — too low for a high-probability setup</p>
                    <p className="text-yellow-500 text-[11px] mt-2 font-semibold">Wait for score above 50+ before entering</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div className="bg-gray-800/30 rounded-lg p-2">
                      <span className="text-gray-500 text-[9px] block">SUPPORT</span>
                      <span className="text-green-400 font-bold text-sm">{support}</span>
                      <span className="text-gray-600 text-[9px] block">Max PE OI</span>
                    </div>
                    <div className="bg-gray-800/30 rounded-lg p-2">
                      <span className="text-gray-500 text-[9px] block">RESISTANCE</span>
                      <span className="text-red-400 font-bold text-sm">{resistance}</span>
                      <span className="text-gray-600 text-[9px] block">Max CE OI</span>
                    </div>
                  </div>
                </div>
              )
            }

            return (
              <div className="space-y-2">
                {/* Main trade box */}
                <div className={`rounded-xl border p-3 ${bull ? 'border-green-600/50 bg-emerald-950/30' : bear ? 'border-red-600/50 bg-red-950/30' : 'border-gray-600 bg-gray-800/30'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xl font-black ${bull ? 'text-green-400' : bear ? 'text-red-400' : 'text-gray-300'}`}>
                        {bull ? '🟢 BUY CALL' : bear ? '🔴 BUY PUT' : '⚪ WAIT'}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-extrabold ${STR_CLR[strength] || 'bg-gray-700 text-gray-400'}`}>{strength}</span>
                    </div>
                    <span className={`text-lg font-black font-mono ${bull ? 'text-green-400' : bear ? 'text-red-400' : 'text-gray-400'}`}>{score.toFixed(0)}%</span>
                  </div>
                  {primary ? (
                    <div className="grid grid-cols-5 gap-1 text-center">
                      <div className="bg-black/20 rounded-lg p-2">
                        <span className="text-gray-400 text-[9px] block font-bold">STRIKE</span>
                        <span className="text-white font-extrabold text-[14px]">{primary.strike}</span>
                      </div>
                      <div className="bg-black/20 rounded-lg p-2">
                        <span className="text-gray-400 text-[9px] block font-bold">ENTRY</span>
                        <span className="text-cyan-400 font-extrabold text-[14px]">{primary.cmp}</span>
                      </div>
                      <div className="bg-black/20 rounded-lg p-2">
                        <span className="text-gray-400 text-[9px] block font-bold">TARGET</span>
                        <span className="text-green-400 font-extrabold text-[14px]">{primary.target1}</span>
                      </div>
                      <div className="bg-black/20 rounded-lg p-2">
                        <span className="text-gray-400 text-[9px] block font-bold">STOP LOSS</span>
                        <span className="text-red-400 font-extrabold text-[14px]">{primary.stop_loss}</span>
                      </div>
                      <div className="bg-black/20 rounded-lg p-2">
                        <span className="text-gray-400 text-[9px] block font-bold">TIME</span>
                        <span className="text-yellow-400 font-bold text-[11px]">{primary.time_limit}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-400 text-[11px] font-mono">Signal building... {dir} bias detected at {score.toFixed(0)}%</p>
                  )}
                </div>
                {/* Support/Resistance + Why */}
                <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
                  <div className="bg-green-950/20 border border-green-800/30 rounded-lg p-2">
                    <span className="text-gray-400 text-[9px] block font-bold">SUPPORT</span>
                    <span className="text-green-400 font-extrabold text-sm">{support}</span>
                    <span className="text-gray-600 text-[9px] block">Max PE OI</span>
                  </div>
                  <div className="bg-red-950/20 border border-red-800/30 rounded-lg p-2">
                    <span className="text-gray-400 text-[9px] block font-bold">RESISTANCE</span>
                    <span className="text-red-400 font-extrabold text-sm">{resistance}</span>
                    <span className="text-gray-600 text-[9px] block">Max CE OI</span>
                  </div>
                  <div className="bg-gray-800/30 border border-gray-700/30 rounded-lg p-2">
                    <span className="text-gray-400 text-[9px] block font-bold">RANGE</span>
                    <span className="text-cyan-400 font-extrabold text-sm">{support}—{resistance}</span>
                    <span className="text-gray-600 text-[9px] block">OI-based range</span>
                  </div>
                </div>
                {/* Quick reason */}
                <div className="text-[10px] text-gray-300 bg-gray-800/20 rounded-lg p-2 border border-gray-700/30 space-y-0.5">
                  <p className="text-gray-500 font-bold uppercase text-[9px]">Why this trade?</p>
                  {confluence.firing?.slice(0, 4).map((f, i) => (
                    <p key={i} className="text-gray-300">• <span className={`font-bold ${f.status === 'CRITICAL' ? 'text-green-400' : f.status === 'ALERT' ? 'text-yellow-400' : 'text-gray-400'}`}>{f.name}</span>: {f.metric}</p>
                  ))}
                </div>
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
