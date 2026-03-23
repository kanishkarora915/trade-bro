import { useState } from 'react'
import type { FlowEntry, BrainSignal, SignalHistoryEntry, ChainRow, ConfluenceResult } from '../hooks/useWebSocket'

const TYPE_CLR: Record<string, string> = { BUY: 'text-neon-green', SELL: 'text-neon-red', NEUTRAL: 'text-neon-yellow' }
const TYPE_BG: Record<string, string> = { BUY: 'bg-emerald-950/20 border-emerald-800/20', SELL: 'bg-red-950/20 border-red-800/20', NEUTRAL: 'bg-yellow-950/10 border-yellow-800/10' }
const STATUS_CLR: Record<string, string> = { EXTREME: 'text-neon-red', STRONG: 'text-neon-green', MODERATE: 'text-neon-yellow', MILD: 'text-neon-blue' }

export default function FlowDashboard({
  tape, brain, lastSignal, signalHistory, chain, confluence, spot, atm, onBack
}: {
  tape: FlowEntry[]; brain: BrainSignal; lastSignal?: BrainSignal | null
  signalHistory?: SignalHistoryEntry[]; chain: ChainRow[]; confluence: ConfluenceResult
  spot: number; atm: number; onBack: () => void
}) {
  const [filter, setFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL')
  const [sortBy, setSortBy] = useState<'time' | 'volume' | 'price'>('time')

  const displaySignal = brain.active ? brain : lastSignal
  const isStale = !brain.active && lastSignal?.active

  // Filter & sort tape
  const filtered = [...tape]
    .filter(f => filter === 'ALL' || f.type === filter)
    .reverse()

  if (sortBy === 'volume') filtered.sort((a, b) => b.volume - a.volume)
  else if (sortBy === 'price') filtered.sort((a, b) => b.price - a.price)

  // Hot strikes — top volume from chain
  const hotStrikes = [...chain]
    .map(r => ({
      strike: r.strike,
      ce_vol: r.ce_vol, pe_vol: r.pe_vol,
      ce_oi: r.ce_oi, pe_oi: r.pe_oi,
      ce_ltp: r.ce_ltp, pe_ltp: r.pe_ltp,
      ce_oi_chg: r.ce_oi_chg, pe_oi_chg: r.pe_oi_chg,
      total_vol: r.ce_vol + r.pe_vol,
      is_atm: r.is_atm,
    }))
    .sort((a, b) => b.total_vol - a.total_vol)
    .slice(0, 10)

  const dc = confluence.direction === 'BULLISH' ? 'text-neon-green' : confluence.direction === 'BEARISH' ? 'text-neon-red' : 'text-tb-muted'

  return (
    <div className="h-screen flex flex-col bg-tb-bg overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 bg-tb-card/50 border-b border-tb-border">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-neon-cyan hover:text-neon-cyan/80 text-sm font-bold transition-all">
            ← Main Dashboard
          </button>
          <span className="text-tb-border">|</span>
          <h1 className="text-sm font-extrabold tracking-widest text-neon-purple uppercase">Flow Dashboard</h1>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono">
          <span className="text-tb-muted">NIFTY <span className="text-tb-text font-bold">{spot.toLocaleString('en-IN')}</span></span>
          <span className="text-tb-muted">ATM <span className="text-neon-cyan font-bold">{atm}</span></span>
          <span className={`font-bold ${dc}`}>{confluence.direction} {confluence.score.toFixed(0)}/100</span>
        </div>
      </div>

      {/* Main Grid: 3 columns */}
      <div className="flex-1 grid grid-cols-[1fr_380px_320px] gap-[1px] bg-tb-border overflow-hidden">

        {/* LEFT: Detailed Flow Tape */}
        <div className="bg-tb-bg p-3 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-[11px] font-bold text-neon-purple uppercase tracking-widest">Live Options Flow</h2>
            <div className="flex items-center gap-1">
              {(['ALL', 'BUY', 'SELL'] as const).map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`text-[9px] px-2 py-0.5 rounded font-bold transition-all ${
                    filter === f
                      ? f === 'BUY' ? 'bg-emerald-900/50 text-neon-green' : f === 'SELL' ? 'bg-red-900/50 text-neon-red' : 'bg-tb-surface text-neon-cyan'
                      : 'text-tb-muted hover:text-tb-text'
                  }`}>{f}</button>
              ))}
              <span className="text-tb-border mx-1">|</span>
              {(['time', 'volume', 'price'] as const).map(s => (
                <button key={s} onClick={() => setSortBy(s)}
                  className={`text-[9px] px-1.5 py-0.5 rounded transition-all ${
                    sortBy === s ? 'bg-tb-surface text-neon-cyan font-bold' : 'text-tb-muted hover:text-tb-text'
                  }`}>{s.charAt(0).toUpperCase() + s.slice(1)}</button>
              ))}
            </div>
          </div>

          {/* Table Header */}
          <div className="flex items-center gap-2 px-2 py-1.5 text-[9px] text-tb-muted/60 uppercase tracking-wider border-b border-tb-border font-mono">
            <span className="w-16 shrink-0">Time</span>
            <span className="w-8 shrink-0">Idx</span>
            <span className="w-20 shrink-0">Strike</span>
            <span className="w-14 text-right shrink-0">Price</span>
            <span className="w-16 text-right shrink-0">Volume</span>
            <span className="w-16 text-right shrink-0">OI</span>
            <span className="w-12 shrink-0">Signal</span>
            <span className="flex-1 text-right">Action</span>
          </div>

          {/* Flow Entries */}
          <div className="flex-1 overflow-y-auto font-mono text-[10px] space-y-px">
            {filtered.length === 0 && <p className="text-tb-muted text-center py-8">No flow data yet — waiting for trades...</p>}
            {filtered.map((f, i) => (
              <div key={i} className={`flex items-center gap-2 px-2 py-[5px] rounded border-l-2 ${TYPE_BG[f.type]} hover:bg-tb-surface/30 transition-colors`}>
                <span className="text-tb-muted/60 w-16 shrink-0">
                  {new Date(f.time).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className="text-tb-muted w-8 shrink-0">{f.index.slice(0, 3)}</span>
                <span className="text-tb-text font-semibold w-20 shrink-0">{f.strike}</span>
                <span className="text-tb-text w-14 text-right shrink-0">₹{f.price.toFixed(1)}</span>
                <span className={`w-16 text-right shrink-0 ${f.volume > 5000 ? 'text-neon-yellow font-bold' : 'text-tb-muted'}`}>
                  {f.volume.toLocaleString()}
                </span>
                <span className="text-tb-muted w-16 text-right shrink-0">{f.oi.toLocaleString()}</span>
                <span className={`font-bold w-12 shrink-0 ${TYPE_CLR[f.type]}`}>
                  {f.type === 'BUY' ? '▲ BUY' : f.type === 'SELL' ? '▼ SELL' : '● NEUT'}
                </span>
                <span className="flex-1 text-right text-[9px]">
                  {f.volume > 5000 && <span className="bg-neon-yellow/20 text-neon-yellow px-1 py-0.5 rounded">BIG</span>}
                  {f.volume > 20000 && <span className="bg-neon-red/20 text-neon-red px-1 py-0.5 rounded ml-1">BLOCK</span>}
                </span>
              </div>
            ))}
          </div>

          {/* Summary bar */}
          <div className="shrink-0 flex items-center justify-between mt-2 pt-2 border-t border-tb-border text-[10px] font-mono">
            <span className="text-tb-muted">{filtered.length} entries</span>
            <div className="flex gap-3">
              <span className="text-neon-green">BUY: {tape.filter(t => t.type === 'BUY').length}</span>
              <span className="text-neon-red">SELL: {tape.filter(t => t.type === 'SELL').length}</span>
              <span className="text-neon-yellow">NEUTRAL: {tape.filter(t => t.type === 'NEUTRAL').length}</span>
            </div>
          </div>
        </div>

        {/* CENTER: Hot Strikes + Trade Signal */}
        <div className="bg-tb-bg p-3 flex flex-col gap-3 overflow-y-auto">
          {/* Active Trade Signal — ALWAYS VISIBLE */}
          <div className={`border rounded-xl p-4 ${
            displaySignal?.active
              ? isStale ? 'border-neon-yellow/30 bg-yellow-950/10' : 'border-neon-green/30 bg-emerald-950/10'
              : 'border-tb-border bg-tb-card/20'
          }`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[11px] font-extrabold uppercase tracking-widest text-neon-green">
                {displaySignal?.active ? (isStale ? '⚡ LAST SIGNAL' : '🔥 LIVE TRADE SIGNAL') : '📊 WAITING FOR SIGNAL'}
              </h3>
              {displaySignal?.strength && (
                <span className={`text-[9px] px-2 py-0.5 rounded font-bold ${STATUS_CLR[displaySignal.strength] || 'text-tb-muted'} bg-tb-surface`}>
                  {displaySignal.strength}
                </span>
              )}
            </div>

            {displaySignal?.active && displaySignal.primary ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-tb-bg/50 rounded-lg p-3 border border-emerald-800/20">
                    <p className="text-[9px] text-tb-muted uppercase mb-1">Primary Entry</p>
                    <p className="text-lg font-black text-neon-green">{displaySignal.primary.strike}</p>
                    <p className="text-sm font-bold text-tb-text mt-1">CMP: {displaySignal.primary.cmp}</p>
                  </div>
                  <div className="space-y-2">
                    <div className="bg-emerald-950/20 rounded-lg p-2 border border-emerald-800/15">
                      <p className="text-[9px] text-tb-muted">TARGET 1</p>
                      <p className="text-sm font-bold text-neon-green">{displaySignal.primary.target1}</p>
                    </div>
                    <div className="bg-emerald-950/20 rounded-lg p-2 border border-emerald-800/15">
                      <p className="text-[9px] text-tb-muted">TARGET 2</p>
                      <p className="text-sm font-bold text-neon-green">{displaySignal.primary.target2}</p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-red-950/20 rounded-lg p-3 border border-red-800/20">
                    <p className="text-[9px] text-tb-muted uppercase mb-1">Stop Loss</p>
                    <p className="text-lg font-black text-neon-red">{displaySignal.primary.stop_loss}</p>
                  </div>
                  <div className="bg-tb-bg/50 rounded-lg p-3 border border-tb-border">
                    <p className="text-[9px] text-tb-muted uppercase mb-1">Time Limit</p>
                    <p className="text-[11px] font-semibold text-neon-yellow">{displaySignal.primary.time_limit}</p>
                  </div>
                </div>

                {/* Secondary */}
                {displaySignal.secondary && (
                  <div className="bg-orange-950/10 rounded-lg p-3 border border-orange-800/15">
                    <p className="text-[9px] text-neon-orange font-bold uppercase mb-1.5">Secondary (OTM Aggressive)</p>
                    <div className="grid grid-cols-4 gap-2 text-[10px] font-mono">
                      <div><span className="text-tb-muted block text-[8px]">BUY</span><span className="text-neon-orange font-bold">{displaySignal.secondary.strike}</span></div>
                      <div><span className="text-tb-muted block text-[8px]">CMP</span><span className="text-tb-text">{displaySignal.secondary.cmp}</span></div>
                      <div><span className="text-tb-muted block text-[8px]">TARGET</span><span className="text-neon-green">{displaySignal.secondary.target}</span></div>
                      <div><span className="text-tb-muted block text-[8px]">SL</span><span className="text-neon-red">{displaySignal.secondary.stop_loss}</span></div>
                    </div>
                  </div>
                )}

                {/* Exit Rules */}
                {displaySignal.exit_rules?.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-tb-border">
                    <p className="text-[9px] text-tb-muted uppercase tracking-widest">Exit Rules</p>
                    {displaySignal.exit_rules.map((r, i) => (
                      <p key={i} className="text-[10px] text-tb-muted"><span className="text-neon-yellow font-semibold">{r.rule}:</span> {r.detail}</p>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-tb-muted text-sm">{brain.message || 'Waiting for confluence signal...'}</p>
                <p className="text-[9px] text-tb-muted/50 mt-1">Score: {confluence.score.toFixed(0)}/100 — Need strong detector alignment</p>
              </div>
            )}
          </div>

          {/* Hot Strikes Table */}
          <div className="border border-tb-border rounded-xl p-3 flex-1 overflow-hidden flex flex-col">
            <h3 className="text-[11px] font-bold text-neon-cyan uppercase tracking-widest mb-2">Hot Strikes — Top Volume</h3>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-[10px] font-mono">
                <thead className="sticky top-0 bg-tb-bg">
                  <tr className="text-tb-muted/60 text-[9px] uppercase">
                    <th className="py-1 text-left">Strike</th>
                    <th className="py-1 text-right">CE Vol</th>
                    <th className="py-1 text-right">PE Vol</th>
                    <th className="py-1 text-right">CE OI Chg</th>
                    <th className="py-1 text-right">PE OI Chg</th>
                    <th className="py-1 text-right">CE LTP</th>
                    <th className="py-1 text-right">PE LTP</th>
                  </tr>
                </thead>
                <tbody>
                  {hotStrikes.map(s => (
                    <tr key={s.strike} className={`border-b border-tb-border/20 ${s.is_atm ? 'bg-neon-cyan/5' : 'hover:bg-tb-surface/30'}`}>
                      <td className={`py-1.5 font-bold ${s.is_atm ? 'text-neon-cyan' : 'text-tb-text'}`}>{s.strike} {s.is_atm ? '★' : ''}</td>
                      <td className={`py-1.5 text-right ${s.ce_vol > 10000 ? 'text-neon-green font-bold' : 'text-tb-text'}`}>{s.ce_vol.toLocaleString()}</td>
                      <td className={`py-1.5 text-right ${s.pe_vol > 10000 ? 'text-neon-red font-bold' : 'text-tb-text'}`}>{s.pe_vol.toLocaleString()}</td>
                      <td className={`py-1.5 text-right ${s.ce_oi_chg > 0 ? 'text-neon-green' : s.ce_oi_chg < 0 ? 'text-neon-red' : 'text-tb-muted'}`}>
                        {s.ce_oi_chg > 0 ? '+' : ''}{(s.ce_oi_chg / 1000).toFixed(1)}K
                      </td>
                      <td className={`py-1.5 text-right ${s.pe_oi_chg > 0 ? 'text-neon-green' : s.pe_oi_chg < 0 ? 'text-neon-red' : 'text-tb-muted'}`}>
                        {s.pe_oi_chg > 0 ? '+' : ''}{(s.pe_oi_chg / 1000).toFixed(1)}K
                      </td>
                      <td className="py-1.5 text-right text-tb-text">₹{s.ce_ltp.toFixed(1)}</td>
                      <td className="py-1.5 text-right text-tb-text">₹{s.pe_ltp.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* RIGHT: Signal History + Stats */}
        <div className="bg-tb-bg p-3 flex flex-col gap-3 overflow-y-auto">
          {/* Trade Stats */}
          <div className="border border-tb-border rounded-xl p-3">
            <h3 className="text-[11px] font-bold text-neon-yellow uppercase tracking-widest mb-2">Session Stats</h3>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
              <div className="bg-tb-surface/30 rounded-lg p-2">
                <p className="text-tb-muted text-[8px]">Total Flows</p>
                <p className="text-tb-text font-bold text-lg">{tape.length}</p>
              </div>
              <div className="bg-tb-surface/30 rounded-lg p-2">
                <p className="text-tb-muted text-[8px]">Signals Today</p>
                <p className="text-neon-green font-bold text-lg">{signalHistory?.length || 0}</p>
              </div>
              <div className="bg-emerald-950/20 rounded-lg p-2">
                <p className="text-tb-muted text-[8px]">Buy Flow</p>
                <p className="text-neon-green font-bold">{tape.filter(t => t.type === 'BUY').length}</p>
              </div>
              <div className="bg-red-950/20 rounded-lg p-2">
                <p className="text-tb-muted text-[8px]">Sell Flow</p>
                <p className="text-neon-red font-bold">{tape.filter(t => t.type === 'SELL').length}</p>
              </div>
            </div>
          </div>

          {/* Big Volume Alerts */}
          <div className="border border-neon-yellow/20 rounded-xl p-3 flex-shrink-0">
            <h3 className="text-[11px] font-bold text-neon-yellow uppercase tracking-widest mb-2">Big Volume Alerts</h3>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {tape.filter(t => t.volume > 5000).reverse().slice(0, 10).map((f, i) => (
                <div key={i} className={`flex items-center gap-2 text-[10px] font-mono py-0.5 ${TYPE_CLR[f.type]}`}>
                  <span className="text-tb-muted/50 w-12">{new Date(f.time).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' })}</span>
                  <span className="font-bold">{f.strike}</span>
                  <span className="ml-auto">{f.volume.toLocaleString()}</span>
                </div>
              ))}
              {tape.filter(t => t.volume > 5000).length === 0 && (
                <p className="text-tb-muted text-[10px] text-center py-2">No big volume trades yet</p>
              )}
            </div>
          </div>

          {/* Signal History — Full */}
          <div className="border border-tb-border rounded-xl p-3 flex-1 overflow-hidden flex flex-col">
            <h3 className="text-[11px] font-bold text-neon-green uppercase tracking-widest mb-2">Signal History</h3>
            <div className="flex-1 overflow-y-auto space-y-2">
              {(!signalHistory || signalHistory.length === 0) && (
                <p className="text-tb-muted text-[10px] text-center py-4">No signals generated yet today</p>
              )}
              {signalHistory && [...signalHistory].reverse().map((sig, i) => (
                <div key={i} className={`border rounded-lg p-2.5 ${
                  sig.direction === 'BULLISH' ? 'border-emerald-800/20 bg-emerald-950/10' : 'border-red-800/20 bg-red-950/10'
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[11px] font-bold ${sig.direction === 'BULLISH' ? 'text-neon-green' : 'text-neon-red'}`}>
                      {sig.direction === 'BULLISH' ? '▲' : '▼'} {sig.primary?.strike || '—'}
                    </span>
                    <span className="text-[8px] text-tb-muted">
                      {sig.recorded_at ? new Date(sig.recorded_at).toLocaleTimeString('en-IN', { hour12: false }) : ''}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 text-[9px] font-mono">
                    <div><span className="text-tb-muted">Entry:</span> <span className="text-tb-text">{sig.primary?.cmp}</span></div>
                    <div><span className="text-tb-muted">T1:</span> <span className="text-neon-green">{sig.primary?.target1}</span></div>
                    <div><span className="text-tb-muted">SL:</span> <span className="text-neon-red">{sig.primary?.stop_loss}</span></div>
                  </div>
                  <div className="text-[8px] text-tb-muted mt-1">
                    NIFTY @ {sig.spot_at_signal?.toLocaleString('en-IN')} | Score: {sig.score}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
