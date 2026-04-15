/**
 * SNIPER — Phased Position Builder
 * SCAN → SCOUT (1 lot) → BUILD (+2 lots) → RIDE (trail) → EXIT
 * Enter EARLY, build as confirmation comes, exit on OI reversal.
 */

const PHASE_STYLES: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  SCAN: { bg: 'bg-gray-900/30', border: 'border-gray-700', text: 'text-gray-400', icon: '🔍' },
  SCOUT: { bg: 'bg-yellow-950/15', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: '🎯' },
  BUILD: { bg: 'bg-blue-950/15', border: 'border-blue-500/30', text: 'text-blue-400', icon: '🏗️' },
  RIDE: { bg: 'bg-emerald-950/15', border: 'border-emerald-500/30', text: 'text-emerald-400', icon: '🚀' },
}

export default function Sniper({ state }: { state: any }) {
  const s = (state as any).sniper || { phase: 'SCAN', position: null }
  const ps = PHASE_STYLES[s.phase] || PHASE_STYLES.SCAN
  const pos = s.position

  return (
    <div className="h-full flex flex-col bg-[#050508] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-gradient-to-r from-[#0a0a10] to-[#080808] border-b border-yellow-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-xl flex items-center justify-center text-[12px] font-black text-black">S</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.2em] text-yellow-400">SNIPER</h1>
              <p className="text-[9px] text-yellow-800">Enter early. Build smart. Ride the move. Exit before reversal.</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono">
            <span className="text-gray-500">Direction <span className={`font-bold ${s.direction === 'BULLISH' ? 'text-emerald-400' : s.direction === 'BEARISH' ? 'text-red-400' : 'text-gray-400'}`}>{s.direction || 'NEUTRAL'}</span></span>
            <span className="text-gray-500">Net <span className={`font-bold ${(s.net_votes || 0) > 0 ? 'text-emerald-400' : (s.net_votes || 0) < 0 ? 'text-red-400' : 'text-gray-400'}`}>{s.net_votes > 0 ? '+' : ''}{s.net_votes || 0}</span></span>
            <span className="text-gray-500">Score <span className="text-yellow-400 font-bold">{s.conf_score || 0}</span></span>
            <span className="text-gray-500">{s.regime || ''}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Phase Indicator */}
        <div className="flex gap-1">
          {['SCAN', 'SCOUT', 'BUILD', 'RIDE'].map(phase => {
            const active = s.phase === phase
            const past = ['SCAN', 'SCOUT', 'BUILD', 'RIDE'].indexOf(s.phase) > ['SCAN', 'SCOUT', 'BUILD', 'RIDE'].indexOf(phase)
            return (
              <div key={phase} className={`flex-1 text-center rounded-xl py-2 border transition-all ${
                active ? `${PHASE_STYLES[phase].border} ${PHASE_STYLES[phase].bg}` :
                past ? 'border-emerald-800/20 bg-emerald-950/5' : 'border-gray-800/50 bg-gray-900/20'
              }`}>
                <p className={`text-[10px] font-black ${active ? PHASE_STYLES[phase].text : past ? 'text-emerald-700' : 'text-gray-700'}`}>
                  {PHASE_STYLES[phase].icon} {phase}
                </p>
                <p className="text-[8px] text-gray-600 mt-0.5">
                  {phase === 'SCAN' ? 'Watching' : phase === 'SCOUT' ? '1 lot' : phase === 'BUILD' ? '+2 lots' : 'Trail SL'}
                </p>
              </div>
            )
          })}
        </div>

        {/* Active Position */}
        {pos ? (
          <div className={`border-2 rounded-2xl p-5 ${ps.border} ${ps.bg}`}>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-lg font-black ${ps.text}`}>{ps.icon} {s.phase} — {pos.strike}</span>
              <div className="text-right">
                <p className={`text-xl font-black font-mono ${(pos.pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {(pos.pnl_pct || 0) >= 0 ? '+' : ''}{pos.pnl_pct || 0}%
                </p>
                <p className={`text-[10px] font-mono ${(pos.pnl_abs || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  ₹{(pos.pnl_abs || 0).toLocaleString('en-IN')}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-x-6 gap-y-2 text-xs font-mono mb-3">
              <div><span className="text-gray-500">Avg Entry</span><br/><span className="text-white font-bold text-sm">₹{pos.avg_entry}</span></div>
              <div><span className="text-gray-500">Current</span><br/><span className={`font-bold text-sm ${(pos.pnl_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>₹{pos.current_ltp}</span></div>
              <div><span className="text-gray-500">Stop Loss</span><br/><span className="text-red-400 font-bold text-sm">₹{pos.stop_loss}</span></div>
              <div><span className="text-gray-500">Lots</span><br/><span className="text-white font-bold">{pos.total_lots} × {pos.lot_size} qty</span></div>
              <div><span className="text-gray-500">Capital</span><br/><span className="text-white">₹{(pos.capital_used || 0).toLocaleString('en-IN')}</span></div>
              <div><span className="text-gray-500">Direction</span><br/><span className={pos.direction === 'BULLISH' ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>{pos.direction}</span></div>
            </div>

            {/* Targets */}
            <div className="flex gap-3 text-[10px] font-mono">
              <span className="text-emerald-400">T1: ₹{pos.target1} (+30%)</span>
              <span className="text-emerald-300">T2: ₹{pos.target2} (+60%)</span>
              <span className="text-gray-500">IV: {pos.iv?.toFixed(1) || '—'}%</span>
            </div>

            {/* Entry log */}
            {s.entries?.length > 0 && (
              <div className="mt-3 border-t border-gray-800/50 pt-2">
                <p className="text-[8px] text-gray-600 uppercase mb-1">Entry Log</p>
                {s.entries.map((e: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[9px] font-mono py-0.5">
                    <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                      e.phase === 'SCOUT' ? 'bg-yellow-900/40 text-yellow-400' :
                      e.phase === 'BUILD' ? 'bg-blue-900/40 text-blue-400' : 'bg-gray-800 text-gray-500'
                    }`}>{e.phase}</span>
                    <span className="text-white">{e.lots} lot @ ₹{e.price}</span>
                    <span className="text-gray-600 ml-auto">{e.time?.split('T')[1]?.slice(0, 8) || ''}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className={`border rounded-2xl p-5 ${ps.border} ${ps.bg}`}>
            <p className={`text-lg font-black ${ps.text} mb-2`}>🔍 SCANNING</p>
            <p className="text-[11px] text-gray-400">
              Watching for early OI shifts, dealer moves, seller patterns.
              Scout entry at Net ≥{s.phase_thresholds?.scout?.split(',')[0]?.replace('Net ≥', '') || '3'} votes.
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[9px]">
              <div className="bg-yellow-950/20 rounded-lg p-2">
                <p className="text-yellow-400 font-bold">SCOUT</p>
                <p className="text-gray-500">{s.phase_thresholds?.scout || 'Net ≥3'}</p>
              </div>
              <div className="bg-blue-950/20 rounded-lg p-2">
                <p className="text-blue-400 font-bold">BUILD</p>
                <p className="text-gray-500">{s.phase_thresholds?.build || 'Net ≥5'}</p>
              </div>
              <div className="bg-emerald-950/20 rounded-lg p-2">
                <p className="text-emerald-400 font-bold">RIDE</p>
                <p className="text-gray-500">{s.phase_thresholds?.ride || 'Net ≥7'}</p>
              </div>
            </div>
          </div>
        )}

        {/* Vote Breakdown */}
        <div className="border border-gray-800 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">Direction Votes</p>
            <span className={`text-sm font-black font-mono ${(s.net_votes || 0) > 0 ? 'text-emerald-400' : (s.net_votes || 0) < 0 ? 'text-red-400' : 'text-gray-500'}`}>
              NET: {(s.net_votes || 0) > 0 ? '+' : ''}{s.net_votes || 0}
            </span>
          </div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-emerald-400 text-[10px] font-mono w-16">BULL {s.bull_votes || 0}</span>
            <div className="flex-1 h-3 bg-gray-800 rounded-full flex overflow-hidden">
              {(s.bull_votes || 0) + (s.bear_votes || 0) > 0 && (
                <>
                  <div className="bg-emerald-500 transition-all" style={{ width: `${(s.bull_votes || 0) / ((s.bull_votes || 0) + (s.bear_votes || 0)) * 100}%` }} />
                  <div className="bg-red-500 flex-1" />
                </>
              )}
            </div>
            <span className="text-red-400 text-[10px] font-mono w-16 text-right">BEAR {s.bear_votes || 0}</span>
          </div>
          {/* Reasons */}
          {s.reasons?.length > 0 && (
            <div className="space-y-0.5 mt-2">
              {s.reasons.map((r: string, i: number) => (
                <p key={i} className="text-[9px] text-gray-500">• {r}</p>
              ))}
            </div>
          )}
        </div>

        {/* Alerts Feed */}
        {s.alerts?.length > 0 && (
          <div className="border border-gray-800 rounded-xl p-3">
            <p className="text-[9px] text-yellow-500 uppercase tracking-widest font-bold mb-2">Activity Log</p>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {[...(s.alerts || [])].reverse().map((a: any, i: number) => (
                <div key={i} className={`flex items-start gap-2 text-[10px] py-1 border-b border-gray-900/30 last:border-0 ${
                  a.type === 'SL_HIT' ? 'text-red-400' :
                  a.type === 'SCOUT' || a.type === 'BUILD' || a.type === 'RIDE' ? 'text-yellow-400' :
                  a.type === 'TRAIL_SL' ? 'text-blue-400' :
                  a.type === 'T2_HIT' ? 'text-emerald-400' : 'text-gray-400'
                }`}>
                  <span className="text-gray-600 font-mono shrink-0 w-14">{a.time}</span>
                  <span className="font-mono font-bold shrink-0 w-16">{a.type}</span>
                  <span className="flex-1">{a.msg}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Closed Trades */}
        {s.closed_trades?.length > 0 && (
          <div className="border border-gray-800 rounded-xl p-3">
            <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold mb-2">Closed Positions</p>
            {s.closed_trades.map((t: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[10px] font-mono py-1.5 border-b border-gray-900/30 last:border-0">
                <span className={(t.exit_pnl || 0) > 0 ? 'text-emerald-400' : 'text-red-400'}>{(t.exit_pnl || 0) > 0 ? '✅' : '❌'}</span>
                <span className="text-white">{t.strike}</span>
                <span className="text-gray-500">₹{t.avg_entry} → ₹{t.exit_price}</span>
                <span className={`ml-auto font-bold ${(t.exit_pnl || 0) > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {(t.exit_pnl || 0) > 0 ? '+' : ''}{t.exit_pnl}%
                </span>
                <span className="text-gray-600">{t.exit_reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* How it works */}
        <div className="border border-gray-800 rounded-xl p-2 text-[8px] text-gray-600 grid grid-cols-4 gap-2">
          <span>SCOUT: 1 lot, tight SL, early entry</span>
          <span>BUILD: +2 lots on confirmation, SL → breakeven</span>
          <span>RIDE: Trail SL from OI walls, let it run</span>
          <span>EXIT: OI reversal / SL / T2 hit / 30 min timeout</span>
        </div>
      </div>
    </div>
  )
}
