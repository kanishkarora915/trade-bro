import { useMemo } from 'react'
import type { TradeState, SignalHistoryEntry, ChainRow } from '../hooks/useWebSocket'

interface Props { state: TradeState; onBack: () => void }

/* ─── helpers ─── */
function fmtTime(t: string): string {
  if (!t) return '--:--'
  try {
    if (/^\d{2}:\d{2}(:\d{2})?$/.test(t)) return t.slice(0, 5)
    const d = new Date(t.includes('+') || t.includes('Z') ? t : t + '+05:30')
    return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0')
  } catch { return '--:--' }
}

function parseNum(s: string | number | undefined): number {
  if (s === undefined || s === null) return 0
  if (typeof s === 'number') return s
  return parseFloat(s.replace(/[₹,]/g, '')) || 0
}

interface JournalEntry {
  time: string
  direction: string
  strike: string
  entry: number
  target: number
  sl: number
  status: 'OPEN' | 'TARGET HIT' | 'SL HIT'
  pnl: number
}

function buildJournal(signals: SignalHistoryEntry[], currentSpot: number): JournalEntry[] {
  return signals
    .filter(s => s.active && s.primary)
    .map(s => {
      const p = s.primary!
      const entry = p.cmp_raw || parseNum(p.cmp)
      const target = parseNum(p.target1)
      const sl = parseNum(p.stop_loss)
      const spot = currentSpot
      const isBull = s.direction === 'BULLISH' || p.action?.includes('BUY')

      let status: JournalEntry['status'] = 'OPEN'
      let pnl = 0

      if (isBull) {
        if (spot >= target && target > 0) { status = 'TARGET HIT'; pnl = target - entry }
        else if (spot <= sl && sl > 0) { status = 'SL HIT'; pnl = sl - entry }
        else { pnl = spot - entry }
      } else {
        if (spot <= target && target > 0) { status = 'TARGET HIT'; pnl = entry - target }
        else if (spot >= sl && sl > 0) { status = 'SL HIT'; pnl = entry - sl }
        else { pnl = entry - spot }
      }

      return {
        time: s.recorded_at || s.timestamp || '',
        direction: s.direction,
        strike: p.strike,
        entry,
        target,
        sl,
        status,
        pnl: Math.round(pnl * 100) / 100,
      }
    })
}

interface HotStrike {
  strike: number
  volume: number
  oi: number
  oiChg: number
  maxVol: number
}

function getHotStrikes(chain: ChainRow[]): { puts: HotStrike[]; calls: HotStrike[] } {
  if (!chain || chain.length === 0) return { puts: [], calls: [] }

  const putStrikes = [...chain]
    .sort((a, b) => b.pe_vol - a.pe_vol)
    .slice(0, 8)
  const callStrikes = [...chain]
    .sort((a, b) => b.ce_vol - a.ce_vol)
    .slice(0, 8)

  const maxPutVol = Math.max(...putStrikes.map(r => r.pe_vol), 1)
  const maxCallVol = Math.max(...callStrikes.map(r => r.ce_vol), 1)

  return {
    puts: putStrikes.map(r => ({ strike: r.strike, volume: r.pe_vol, oi: r.pe_oi, oiChg: r.pe_oi_chg, maxVol: maxPutVol })),
    calls: callStrikes.map(r => ({ strike: r.strike, volume: r.ce_vol, oi: r.ce_oi, oiChg: r.ce_oi_chg, maxVol: maxCallVol })),
  }
}

/* ─── sub-components ─── */

function HotStrikesSection({ chain }: { chain: ChainRow[] }) {
  const { puts, calls } = useMemo(() => getHotStrikes(chain), [chain])

  const StrikeTable = ({ title, subtitle, color, data }: { title: string; subtitle: string; color: 'green' | 'red'; data: HotStrike[] }) => {
    const hdrBg = color === 'green' ? 'bg-green-900/20' : 'bg-red-900/20'
    const hdrTxt = color === 'green' ? 'text-green-400' : 'text-red-400'
    const barBg = color === 'green' ? 'bg-green-500/60' : 'bg-red-500/60'
    return (
      <div className="flex-1 min-w-0">
        <div className={`flex items-center gap-2 px-3 py-2 ${hdrBg} rounded-t-lg`}>
          <span className={`text-xs font-extrabold ${hdrTxt}`}>{title}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${hdrBg} ${hdrTxt}`}>{subtitle}</span>
        </div>
        <table className="w-full text-[10px] font-mono">
          <thead>
            <tr className="text-gray-500 border-b border-tb-border">
              <th className="text-left px-3 py-1.5 font-medium w-20">Strike</th>
              <th className="text-left px-2 py-1.5 font-medium">Volume</th>
              <th className="text-right px-2 py-1.5 font-medium w-20">Vol</th>
              <th className="text-right px-2 py-1.5 font-medium w-24">OI</th>
              <th className="text-right px-3 py-1.5 font-medium w-20">OI Chg</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-tb-border/50 hover:bg-white/[0.02]">
                <td className="px-3 py-1.5 text-white font-bold">{row.strike.toLocaleString('en-IN')}</td>
                <td className="px-2 py-1.5">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-3 bg-gray-800 rounded overflow-hidden">
                      <div className={`h-full ${barBg} rounded`} style={{ width: `${(row.volume / row.maxVol) * 100}%` }} />
                    </div>
                  </div>
                </td>
                <td className="px-2 py-1.5 text-right text-gray-300">{row.volume.toLocaleString('en-IN')}</td>
                <td className="px-2 py-1.5 text-right text-gray-300">{row.oi.toLocaleString('en-IN')}</td>
                <td className={`px-3 py-1.5 text-right font-semibold ${row.oiChg > 0 ? 'text-green-400' : row.oiChg < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                  {row.oiChg > 0 ? '+' : ''}{row.oiChg.toLocaleString('en-IN')}
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={5} className="text-center py-4 text-gray-600">No chain data</td></tr>
            )}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="bg-tb-card/40 rounded-xl border border-tb-border">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-tb-border">
        <span className="text-sm font-extrabold text-white">HOT STRIKES</span>
        <span className="text-[9px] text-gray-500 font-mono">Support &amp; Resistance from Option Activity</span>
      </div>
      <div className="flex gap-4 p-3">
        <StrikeTable title="MAX PUT SELLING" subtitle="SUPPORT" color="green" data={puts} />
        <StrikeTable title="MAX CALL SELLING" subtitle="RESISTANCE" color="red" data={calls} />
      </div>
    </div>
  )
}

function TradeJournal({ journal }: { journal: JournalEntry[] }) {
  return (
    <div className="bg-tb-card/40 rounded-xl border border-tb-border flex-1 min-w-0 flex flex-col">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-tb-border shrink-0">
        <span className="text-sm font-extrabold text-white">TRADE JOURNAL</span>
        <span className="text-[9px] text-gray-500 font-mono">{journal.length} signals today</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-[10px] font-mono">
          <thead className="sticky top-0 bg-tb-bg z-10">
            <tr className="text-gray-500 border-b border-tb-border">
              <th className="text-left px-3 py-1.5 font-medium">Time</th>
              <th className="text-left px-2 py-1.5 font-medium">Dir</th>
              <th className="text-left px-2 py-1.5 font-medium">Strike</th>
              <th className="text-right px-2 py-1.5 font-medium">Entry</th>
              <th className="text-right px-2 py-1.5 font-medium">Target</th>
              <th className="text-right px-2 py-1.5 font-medium">SL</th>
              <th className="text-center px-2 py-1.5 font-medium">Status</th>
              <th className="text-right px-3 py-1.5 font-medium">P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {journal.map((t, i) => {
              const statusClr = t.status === 'TARGET HIT' ? 'bg-green-900/30 text-green-400' : t.status === 'SL HIT' ? 'bg-red-900/30 text-red-400' : 'bg-gray-800/50 text-gray-400'
              const pnlClr = t.pnl > 0 ? 'text-green-400' : t.pnl < 0 ? 'text-red-400' : 'text-gray-400'
              const dirClr = t.direction === 'BULLISH' ? 'text-green-400' : t.direction === 'BEARISH' ? 'text-red-400' : 'text-gray-400'
              return (
                <tr key={i} className="border-b border-tb-border/50 hover:bg-white/[0.02]">
                  <td className="px-3 py-1.5 text-gray-400">{fmtTime(t.time)}</td>
                  <td className={`px-2 py-1.5 font-bold ${dirClr}`}>{t.direction?.slice(0, 4)}</td>
                  <td className="px-2 py-1.5 text-white font-bold">{t.strike}</td>
                  <td className="px-2 py-1.5 text-right text-gray-300">{t.entry.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-right text-cyan-400">{t.target.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-right text-orange-400">{t.sl.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-center">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${statusClr}`}>{t.status}</span>
                  </td>
                  <td className={`px-3 py-1.5 text-right font-bold ${pnlClr}`}>
                    {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(1)}
                  </td>
                </tr>
              )
            })}
            {journal.length === 0 && (
              <tr><td colSpan={8} className="text-center py-6 text-gray-600 text-[11px]">No signals generated today</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function AccuracyStats({ journal }: { journal: JournalEntry[] }) {
  const winners = journal.filter(t => t.status === 'TARGET HIT')
  const losers = journal.filter(t => t.status === 'SL HIT')
  const open = journal.filter(t => t.status === 'OPEN')
  const closed = winners.length + losers.length
  const winRate = closed > 0 ? (winners.length / closed) * 100 : 0
  const totalPnl = journal.reduce((s, t) => s + t.pnl, 0)
  const avgPnl = journal.length > 0 ? totalPnl / journal.length : 0
  const bestTrade = journal.length > 0 ? Math.max(...journal.map(t => t.pnl)) : 0
  const worstTrade = journal.length > 0 ? Math.min(...journal.map(t => t.pnl)) : 0
  const accuracy = journal.length > 0 ? winRate : 0

  const StatRow = ({ label, value, color }: { label: string; value: string; color?: string }) => (
    <div className="flex items-center justify-between py-1.5 border-b border-tb-border/30">
      <span className="text-gray-500 text-[10px]">{label}</span>
      <span className={`text-[11px] font-bold font-mono ${color || 'text-white'}`}>{value}</span>
    </div>
  )

  return (
    <div className="bg-tb-card/40 rounded-xl border border-tb-border w-72 shrink-0 flex flex-col">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-tb-border shrink-0">
        <span className="text-sm font-extrabold text-white">ACCURACY</span>
      </div>
      <div className="p-4 flex flex-col items-center gap-2">
        <div className={`text-5xl font-black font-mono ${accuracy >= 60 ? 'text-green-400' : accuracy >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
          {accuracy.toFixed(0)}%
        </div>
        <span className="text-[10px] text-gray-500">Win Rate</span>
      </div>
      <div className="px-4 pb-4 flex-1">
        <StatRow label="Total Signals" value={String(journal.length)} />
        <StatRow label="Winners" value={String(winners.length)} color="text-green-400" />
        <StatRow label="Losers" value={String(losers.length)} color="text-red-400" />
        <StatRow label="Open" value={String(open.length)} color="text-yellow-400" />
        <StatRow label="Avg P&L / Trade" value={`${avgPnl >= 0 ? '+' : ''}${avgPnl.toFixed(1)}`} color={avgPnl >= 0 ? 'text-green-400' : 'text-red-400'} />
        <StatRow label="Best Trade" value={`+${bestTrade.toFixed(1)}`} color="text-green-400" />
        <StatRow label="Worst Trade" value={worstTrade.toFixed(1)} color="text-red-400" />
        <StatRow label="Total P&L" value={`${totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(1)}`} color={totalPnl >= 0 ? 'text-green-400' : 'text-red-400'} />
      </div>
    </div>
  )
}

function exportPDF(journal: JournalEntry[]) {
  const winners = journal.filter(t => t.status === 'TARGET HIT').length
  const losers = journal.filter(t => t.status === 'SL HIT').length
  const closed = winners + losers
  const winRate = closed > 0 ? ((winners / closed) * 100).toFixed(1) : '0'
  const totalPnl = journal.reduce((s, t) => s + t.pnl, 0).toFixed(1)
  const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

  const rows = journal.map(t => `
    <tr style="border-bottom:1px solid #333">
      <td style="padding:6px 8px">${fmtTime(t.time)}</td>
      <td style="padding:6px 8px;color:${t.direction === 'BULLISH' ? '#4ade80' : '#f87171'}">${t.direction}</td>
      <td style="padding:6px 8px;font-weight:bold">${t.strike}</td>
      <td style="padding:6px 8px;text-align:right">${t.entry.toFixed(1)}</td>
      <td style="padding:6px 8px;text-align:right">${t.target.toFixed(1)}</td>
      <td style="padding:6px 8px;text-align:right">${t.sl.toFixed(1)}</td>
      <td style="padding:6px 8px;text-align:center;color:${t.status === 'TARGET HIT' ? '#4ade80' : t.status === 'SL HIT' ? '#f87171' : '#9ca3af'}">${t.status}</td>
      <td style="padding:6px 8px;text-align:right;font-weight:bold;color:${t.pnl >= 0 ? '#4ade80' : '#f87171'}">${t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(1)}</td>
    </tr>
  `).join('')

  const html = `<!DOCTYPE html><html><head><title>TRADE BRO - Trade Report ${today}</title>
<style>
  body{background:#0a0a0f;color:#e5e7eb;font-family:monospace;padding:32px;margin:0}
  h1{color:#22d3ee;margin:0 0 4px}
  .sub{color:#6b7280;font-size:12px;margin-bottom:24px}
  table{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:24px}
  th{text-align:left;padding:8px;color:#6b7280;border-bottom:2px solid #333;font-weight:500}
  .stats{display:flex;gap:24px;margin-bottom:24px}
  .stat-box{background:#111827;border:1px solid #1f2937;border-radius:8px;padding:16px;text-align:center;flex:1}
  .stat-num{font-size:28px;font-weight:900}
  .stat-label{font-size:10px;color:#6b7280;margin-top:4px}
  @media print{body{background:#fff;color:#111}th{color:#666;border-color:#ccc}tr{border-color:#eee!important}.stat-box{background:#f9fafb;border-color:#e5e7eb}}
</style></head><body>
  <h1>TRADE BRO</h1>
  <div class="sub">${today} — Trade Report</div>
  <div class="stats">
    <div class="stat-box"><div class="stat-num" style="color:#22d3ee">${journal.length}</div><div class="stat-label">Total Signals</div></div>
    <div class="stat-box"><div class="stat-num" style="color:#4ade80">${winners}</div><div class="stat-label">Winners</div></div>
    <div class="stat-box"><div class="stat-num" style="color:#f87171">${losers}</div><div class="stat-label">Losers</div></div>
    <div class="stat-box"><div class="stat-num" style="color:${parseFloat(winRate) >= 50 ? '#4ade80' : '#f87171'}">${winRate}%</div><div class="stat-label">Win Rate</div></div>
    <div class="stat-box"><div class="stat-num" style="color:${parseFloat(totalPnl) >= 0 ? '#4ade80' : '#f87171'}">${parseFloat(totalPnl) >= 0 ? '+' : ''}${totalPnl}</div><div class="stat-label">Total P&L</div></div>
  </div>
  <table>
    <thead><tr><th>Time</th><th>Direction</th><th>Strike</th><th style="text-align:right">Entry</th><th style="text-align:right">Target</th><th style="text-align:right">SL</th><th style="text-align:center">Status</th><th style="text-align:right">P&L</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="8" style="text-align:center;padding:24px;color:#6b7280">No signals today</td></tr>'}</tbody>
  </table>
  <div style="text-align:center;color:#374151;font-size:10px;margin-top:32px">Generated by TRADE BRO Analytics</div>
  <script>window.print()</script>
</body></html>`

  const w = window.open('', '_blank')
  if (w) { w.document.write(html); w.document.close() }
}

/* ─── main component ─── */

export default function AnalyticsDashboard({ state, onBack }: Props) {
  const { signal_history, chain_summary, spot } = state

  const journal = useMemo(
    () => buildJournal(signal_history ? [...signal_history].reverse() : [], spot),
    [signal_history, spot]
  )

  return (
    <div className="h-screen flex flex-col bg-tb-bg overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2.5 bg-tb-card/30 border-b border-tb-border">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-[10px] font-bold text-gray-400 hover:text-white border border-tb-border px-3 py-1 rounded-lg transition-all">
            ← Back
          </button>
          <span className="text-sm font-extrabold text-white tracking-wide">ANALYTICS DASHBOARD</span>
          <span className="text-[9px] text-gray-500 font-mono">SPOT {spot.toLocaleString('en-IN')}</span>
        </div>
        <button
          onClick={() => exportPDF(journal)}
          className="text-[10px] font-bold text-neon-cyan border border-neon-cyan/30 px-4 py-1.5 rounded-lg hover:bg-neon-cyan/10 transition-all flex items-center gap-1.5"
        >
          <span>Export Today&apos;s Trades</span>
          <span className="text-[9px] opacity-60">PDF</span>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Section 1: Hot Strikes */}
        <HotStrikesSection chain={chain_summary || []} />

        {/* Section 2 + 3: Journal + Accuracy side by side */}
        <div className="flex gap-4 min-h-[360px]">
          <TradeJournal journal={journal} />
          <AccuracyStats journal={journal} />
        </div>
      </div>
    </div>
  )
}
