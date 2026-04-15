/**
 * COMMAND CENTER — ONE signal, ONE voice.
 * All data merged → single actionable trade.
 * Running trade monitor with ±4 strike OI tracking.
 * Auto-saved trades with daily stats.
 */

export default function CommandCenter({ state }: { state: any }) {
  const cmd = (state as any).command || { signal: 'WAIT', reason: 'Loading...' }
  const isBuy = cmd.signal === 'BUY' || cmd.signal === 'STRONG BUY'
  const isWatch = cmd.signal === 'WATCHLIST'
  const monitor = cmd.position_monitor

  return (
    <div className="h-full flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-gradient-to-r from-gray-900 to-[#0a0a0a] border-b border-cyan-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-xl flex items-center justify-center text-[11px] font-black text-black">CC</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.2em] text-cyan-400">COMMAND CENTER</h1>
              <p className="text-[9px] text-cyan-800">All data → ONE signal → ONE trade. No confusion.</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono">
            <span className="text-gray-500">Capital <span className="text-white font-bold">₹{((cmd.capital || 0) / 100000).toFixed(0)}L</span></span>
            <span className="text-gray-500">SL <span className="text-red-400 font-bold">{cmd.max_sl_pct || '15%'}</span></span>
            {cmd.today_stats && <span className="text-gray-500">Today <span className="text-cyan-400 font-bold">{cmd.today_stats.total_trades || 0} trades</span></span>}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* MARKET INTELLIGENCE STRIP */}
        {(() => {
          const mi = cmd.market_intel || {}
          const regime = mi.regime || {}
          const theta = mi.theta || {}
          const expiry = mi.expiry || {}
          const trade_ok = mi.tradeability || {}
          const regimeClr = regime.color === 'green' ? 'text-emerald-400' : regime.color === 'red' ? 'text-red-400' : regime.color === 'yellow' ? 'text-yellow-400' : regime.color === 'orange' ? 'text-orange-400' : 'text-gray-400'

          return (
            <div className="grid grid-cols-4 gap-2">
              {/* Regime */}
              <div className={`border rounded-xl p-2.5 ${regime.color === 'green' ? 'border-emerald-800/30 bg-emerald-950/10' : regime.color === 'red' ? 'border-red-800/30 bg-red-950/10' : regime.color === 'yellow' ? 'border-yellow-800/30 bg-yellow-950/10' : 'border-gray-800 bg-gray-900/30'}`}>
                <p className="text-[8px] text-gray-600 uppercase">Regime</p>
                <p className={`text-[11px] font-black ${regimeClr}`}>{regime.regime || 'UNKNOWN'}</p>
                <p className="text-[8px] text-gray-600">{regime.range_pts ? `Range: ${regime.range_pts} pts` : ''}</p>
              </div>
              {/* Tradeability */}
              <div className={`border rounded-xl p-2.5 ${trade_ok.verdict === 'GO' ? 'border-emerald-800/30 bg-emerald-950/10' : trade_ok.verdict === 'AVOID' ? 'border-red-800/30 bg-red-950/10' : 'border-yellow-800/30 bg-yellow-950/10'}`}>
                <p className="text-[8px] text-gray-600 uppercase">Trade-ability</p>
                <p className={`text-xl font-black font-mono ${trade_ok.verdict === 'GO' ? 'text-emerald-400' : trade_ok.verdict === 'AVOID' ? 'text-red-400' : 'text-yellow-400'}`}>{trade_ok.score || 0}</p>
                <p className={`text-[8px] font-bold ${trade_ok.verdict === 'GO' ? 'text-emerald-400' : 'text-red-400'}`}>{trade_ok.verdict || 'GO'}</p>
              </div>
              {/* Theta */}
              <div className="border border-gray-800 rounded-xl p-2.5 bg-gray-900/30">
                <p className="text-[8px] text-gray-600 uppercase">Theta Burn</p>
                <p className="text-[11px] font-black text-red-400 font-mono">₹{theta.theta_per_lot_min || 0}/min</p>
                <p className="text-[8px] text-gray-600">30m: ₹{theta.burn_30min || 0}</p>
              </div>
              {/* Expiry */}
              <div className={`border rounded-xl p-2.5 ${expiry.is_expiry ? 'border-red-800/30 bg-red-950/10' : 'border-gray-800 bg-gray-900/30'}`}>
                <p className="text-[8px] text-gray-600 uppercase">Expiry</p>
                <p className={`text-[11px] font-black ${expiry.is_expiry ? 'text-red-400' : 'text-gray-500'}`}>{expiry.mode || 'NORMAL'}</p>
                {expiry.hours_left && <p className="text-[8px] text-gray-600">{expiry.hours_left}h left</p>}
              </div>
            </div>
          )
        })()}

        {/* Regime advice */}
        {cmd.market_intel?.regime?.buyer_advice && (
          <div className={`text-[10px] px-3 py-1.5 rounded-lg ${
            cmd.market_intel.tradeability?.verdict === 'AVOID' ? 'bg-red-950/20 text-red-400' :
            cmd.market_intel.tradeability?.verdict === 'CAUTION' ? 'bg-yellow-950/20 text-yellow-400' :
            'bg-emerald-950/10 text-emerald-400'
          }`}>
            {cmd.market_intel.regime.buyer_advice}
          </div>
        )}

        {/* Theta warning */}
        {cmd.market_intel?.theta?.warning && (
          <div className="text-[10px] px-3 py-1.5 rounded-lg bg-red-950/20 text-red-400">
            ⏱ {cmd.market_intel.theta.warning}
          </div>
        )}

        {/* Expiry rules */}
        {cmd.market_intel?.expiry?.is_expiry && (
          <div className="border border-red-900/30 bg-red-950/10 rounded-xl p-2.5">
            <p className="text-[8px] text-red-500 uppercase tracking-widest font-bold mb-1">Expiry Day Rules</p>
            <div className="grid grid-cols-2 gap-0.5 text-[9px] text-red-400/70">
              {(cmd.market_intel.expiry.rules || []).slice(0, 6).map((r: string, i: number) => (
                <span key={i}>• {r}</span>
              ))}
            </div>
          </div>
        )}

        {/* MAIN SIGNAL */}
        <div className={`border-2 rounded-2xl p-5 ${
          cmd.signal === 'STRONG BUY' ? 'border-cyan-400 bg-cyan-950/20 shadow-[0_0_40px_rgba(6,182,212,0.15)]' :
          isBuy ? 'border-emerald-500/50 bg-emerald-950/15' :
          isWatch ? 'border-yellow-500/30 bg-yellow-950/10' :
          'border-gray-800 bg-gray-900/30'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className={`text-xl font-black ${
                cmd.signal === 'STRONG BUY' ? 'text-cyan-300' :
                isBuy ? 'text-emerald-400' : isWatch ? 'text-yellow-400' : 'text-gray-500'
              }`}>
                {cmd.signal === 'STRONG BUY' ? '⚡' : isBuy ? '▲' : isWatch ? '👁' : '⏸'} {cmd.signal}
              </span>
              {cmd.direction && cmd.direction !== 'NEUTRAL' && (
                <span className={`text-xs font-bold ${cmd.direction === 'BULLISH' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {cmd.direction}
                </span>
              )}
            </div>
            <div className="text-right">
              <p className="text-[9px] text-gray-600">Conviction</p>
              <p className={`text-lg font-black font-mono ${cmd.conviction > 8 ? 'text-cyan-400' : cmd.conviction > 5 ? 'text-emerald-400' : 'text-gray-500'}`}>
                {cmd.conviction || 0}
              </p>
            </div>
          </div>

          {/* Reason */}
          <p className="text-[11px] text-gray-300 leading-relaxed mb-3">{cmd.reason}</p>

          {/* Wait reasons — FIX #5 */}
          {cmd.wait_reasons?.length > 0 && !isBuy && (
            <div className="bg-red-950/10 border border-red-900/20 rounded-lg p-2.5 mb-3">
              <p className="text-[8px] text-red-500 uppercase font-bold mb-1">Why Not Trading</p>
              {cmd.wait_reasons.map((r: string, i: number) => (
                <p key={i} className="text-[9px] text-red-400/80 py-0.5">✗ {r}</p>
              ))}
              {cmd.what_to_change?.length > 0 && (
                <>
                  <p className="text-[8px] text-emerald-600 uppercase font-bold mt-1.5 mb-0.5">What Needs To Change</p>
                  {cmd.what_to_change.map((r: string, i: number) => (
                    <p key={i} className="text-[9px] text-emerald-500/70 py-0.5">→ {r}</p>
                  ))}
                </>
              )}
            </div>
          )}

          {/* Votes breakdown — NET based */}
          {cmd.votes && (
            <div className="flex items-center gap-3 mb-3">
              <div className="flex-1">
                <div className="flex justify-between text-[9px] mb-0.5">
                  <span className="text-emerald-400 font-bold">BULL {cmd.votes.bullish}</span>
                  <span className={`font-bold font-mono ${(cmd.votes.net || 0) > 0 ? 'text-emerald-400' : (cmd.votes.net || 0) < 0 ? 'text-red-400' : 'text-gray-400'}`}>NET {cmd.votes.net > 0 ? '+' : ''}{cmd.votes.net || 0}</span>
                  <span className="text-red-400 font-bold">BEAR {cmd.votes.bearish}</span>
                </div>
                <div className="h-2 bg-gray-800 rounded-full flex overflow-hidden">
                  <div className="bg-emerald-500 transition-all" style={{ width: `${cmd.votes.total > 0 ? (cmd.votes.bullish / cmd.votes.total * 100) : 50}%` }} />
                  <div className="bg-red-500 flex-1" />
                </div>
              </div>
              <div className="flex gap-1.5">
                {[
                  { key: 'ivr', label: `IVR ${cmd.gates?.ivr_value || ''}%` },
                  { key: 'gex', label: `GEX ${((cmd.gates?.gex_value || 0) / 1000).toFixed(0)}K` },
                  { key: 'market', label: cmd.gates?.regime || 'MARKET' },
                ].map(g => {
                  const s = cmd.gates?.[g.key] || 'GREEN'
                  const v = typeof s === 'string' ? s : 'GREEN'
                  return (
                    <span key={g.key} className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${
                      v === 'GREEN' || v === 'OPEN' ? 'bg-emerald-900/40 text-emerald-400' :
                      v === 'RED' || v === 'CLOSED' ? 'bg-red-900/40 text-red-400' :
                      'bg-yellow-900/40 text-yellow-400'
                    }`}>{g.label}</span>
                  )
                })}
              </div>
            </div>
          )}

          {/* Trade details */}
          {cmd.trade && (
            <div className="bg-black/30 rounded-xl p-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs font-mono">
              <div className="flex justify-between"><span className="text-gray-500">STRIKE</span><span className="text-cyan-400 font-bold text-sm">{cmd.trade.strike}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">ENTRY</span><span className="text-white font-bold text-sm">₹{cmd.trade.entry}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">STOP LOSS</span><span className="text-red-400 font-bold">₹{cmd.trade.stop_loss} ({cmd.trade.sl_type || 'FIXED'})</span></div>
              <div className="flex justify-between"><span className="text-gray-500">TARGET 1</span><span className="text-emerald-400">₹{cmd.trade.target1} (+30%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">TARGET 2</span><span className="text-emerald-400">₹{cmd.trade.target2} (+60%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">LOTS</span><span className="text-white font-bold">{cmd.trade.lots} ({cmd.trade.lot_size} qty)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">CAPITAL</span><span className="text-white">₹{(cmd.trade.capital_used || 0).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">MAX LOSS</span><span className="text-red-400">₹{(cmd.trade.max_loss || 0).toLocaleString('en-IN')}</span></div>
            </div>
          )}

          {/* Entry Zone — FIX #4 */}
          {cmd.entry_zone && (
            <div className="bg-blue-950/10 border border-blue-900/20 rounded-lg p-2.5 mt-3">
              <p className="text-[8px] text-blue-400 uppercase font-bold mb-1.5">Entry Timing</p>
              <div className="grid grid-cols-3 gap-2 text-[10px]">
                <div className="bg-emerald-950/20 rounded-lg p-2">
                  <p className="text-emerald-500 font-bold text-[9px]">PULLBACK ENTRY</p>
                  <p className="text-white font-mono font-bold">{cmd.entry_zone.pullback_zone}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">{cmd.entry_zone.pullback_reason}</p>
                </div>
                <div className="bg-blue-950/20 rounded-lg p-2">
                  <p className="text-blue-400 font-bold text-[9px]">BREAKOUT ENTRY</p>
                  <p className="text-white font-mono font-bold">{cmd.entry_zone.breakout_level}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">{cmd.entry_zone.breakout_reason}</p>
                </div>
                <div className="bg-red-950/20 rounded-lg p-2">
                  <p className="text-red-400 font-bold text-[9px]">AVOID ABOVE</p>
                  <p className="text-white font-mono font-bold">{cmd.entry_zone.avoid_above}</p>
                  <p className="text-[8px] text-gray-500 mt-0.5">{cmd.entry_zone.avoid_reason}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* RUNNING TRADE MONITOR */}
        {monitor && (
          <div className="border border-cyan-800/30 bg-cyan-950/10 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[9px] text-cyan-400 uppercase tracking-widest font-bold">Running Trade Monitor</p>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="text-white">LTP ₹{monitor.current_ltp}</span>
                <span className={`font-bold ${monitor.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {monitor.pnl_pct >= 0 ? '+' : ''}{monitor.pnl_pct}% (₹{(monitor.pnl_abs || 0).toLocaleString('en-IN')})
                </span>
              </div>
            </div>

            {/* Alerts */}
            {monitor.alerts?.length > 0 && (
              <div className="space-y-1.5 mb-3">
                {monitor.alerts.map((a: any, i: number) => (
                  <div key={i} className={`border rounded-lg px-3 py-2 ${
                    a.severity === 'CRITICAL' ? 'border-red-500/50 bg-red-950/30 animate-pulse' :
                    a.severity === 'HIGH' ? 'border-orange-500/40 bg-orange-950/20' :
                    'border-gray-700 bg-gray-900/30'
                  }`}>
                    <p className={`text-[10px] font-bold ${a.severity === 'CRITICAL' ? 'text-red-400' : a.severity === 'HIGH' ? 'text-orange-400' : 'text-gray-300'}`}>
                      {a.severity === 'CRITICAL' ? '🚨' : a.severity === 'HIGH' ? '⚠️' : 'ℹ️'} {a.msg}
                    </p>
                    <p className="text-[9px] text-gray-500 mt-0.5">{a.action}</p>
                  </div>
                ))}
              </div>
            )}

            {/* ±4 Strikes OI Map */}
            <div className="grid grid-cols-9 gap-0.5">
              {(monitor.nearby_strikes || []).map((n: any, i: number) => (
                <div key={i} className={`text-center rounded-lg p-1.5 ${
                  n.is_active ? 'bg-cyan-900/40 border border-cyan-500/40' :
                  n.action === 'WRITING' ? 'bg-red-900/20' :
                  n.action === 'COVERING' ? 'bg-emerald-900/20' : 'bg-gray-900/30'
                }`}>
                  <p className={`text-[9px] font-mono font-bold ${n.is_active ? 'text-cyan-400' : 'text-gray-400'}`}>{n.strike}</p>
                  <p className={`text-[8px] font-mono ${
                    n.oi_chg > 0 ? 'text-red-400' : n.oi_chg < 0 ? 'text-emerald-400' : 'text-gray-600'
                  }`}>
                    {n.oi_chg > 0 ? '+' : ''}{(n.oi_chg / 1000).toFixed(0)}K
                  </p>
                  <p className="text-[7px] text-gray-600">{n.action}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Why this direction — reasoning from all sources */}
        {(cmd.reasons_bull?.length > 0 || cmd.reasons_bear?.length > 0) && (
          <div className="grid grid-cols-2 gap-3">
            <div className="border border-emerald-900/20 rounded-xl p-3">
              <p className="text-[9px] text-emerald-500 uppercase tracking-widest font-bold mb-1.5">Bullish Reasons ({cmd.votes?.bullish || 0})</p>
              {(cmd.reasons_bull || []).map((r: string, i: number) => (
                <p key={i} className="text-[9px] text-gray-400 py-0.5 border-b border-gray-900/30 last:border-0">• {r}</p>
              ))}
              {(!cmd.reasons_bull || cmd.reasons_bull.length === 0) && <p className="text-[9px] text-gray-700 italic">None</p>}
            </div>
            <div className="border border-red-900/20 rounded-xl p-3">
              <p className="text-[9px] text-red-500 uppercase tracking-widest font-bold mb-1.5">Bearish Reasons ({cmd.votes?.bearish || 0})</p>
              {(cmd.reasons_bear || []).map((r: string, i: number) => (
                <p key={i} className="text-[9px] text-gray-400 py-0.5 border-b border-gray-900/30 last:border-0">• {r}</p>
              ))}
              {(!cmd.reasons_bear || cmd.reasons_bear.length === 0) && <p className="text-[9px] text-gray-700 italic">None</p>}
            </div>
          </div>
        )}

        {/* TODAY'S P&L STATS */}
        {cmd.today_stats?.total_trades > 0 && (
          <div className="border border-gray-800 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">Today's Performance</p>
              <span className={`text-sm font-black font-mono ${(cmd.today_stats.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                ₹{(cmd.today_stats.total_pnl || 0).toLocaleString('en-IN')}
              </span>
            </div>
            <div className="grid grid-cols-5 gap-2 text-center text-[9px]">
              <div><p className="text-gray-600">Trades</p><p className="text-white font-bold">{cmd.today_stats.total_trades}</p></div>
              <div><p className="text-gray-600">Wins</p><p className="text-emerald-400 font-bold">{cmd.today_stats.wins || 0}</p></div>
              <div><p className="text-gray-600">Losses</p><p className="text-red-400 font-bold">{cmd.today_stats.losses || 0}</p></div>
              <div><p className="text-gray-600">Win Rate</p><p className="text-cyan-400 font-bold">{cmd.today_stats.win_rate || 0}%</p></div>
              <div><p className="text-gray-600">Drawdown</p><p className="text-red-400 font-bold">₹{(cmd.today_stats.max_drawdown || 0).toLocaleString('en-IN')}</p></div>
            </div>
            {/* Recent trades */}
            {cmd.today_stats.trades?.length > 0 && (
              <div className="mt-2 space-y-0.5">
                {cmd.today_stats.trades.slice(-3).map((t: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[9px] font-mono py-0.5 border-t border-gray-900/30">
                    <span className={t.pnl_pct > 0 ? 'text-emerald-400' : 'text-red-400'}>{t.pnl_pct > 0 ? '✅' : '❌'}</span>
                    <span className="text-white">{t.strike}</span>
                    <span className="text-gray-500">₹{t.entry} → ₹{t.exit_price}</span>
                    <span className={`ml-auto font-bold ${t.pnl_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>{t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct}%</span>
                    <span className="text-gray-600">{t.exit_reason}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Rules + Status */}
        <div className="border border-gray-800 rounded-xl p-2 text-[8px] text-gray-600 flex justify-between">
          <span>Capital: ₹10L</span>
          <span>Max SL: 15%</span>
          <span>NIFTY 75 | BN 30 | SENSEX 20</span>
          <span>Paper Trade: ON</span>
          <span className={cmd.telegram_active ? 'text-emerald-400' : 'text-gray-600'}>
            Telegram: {cmd.telegram_active ? 'ON' : 'OFF'}
          </span>
        </div>
      </div>
    </div>
  )
}
