export default function DealerPositions({ state }: { state: any }) {
  const d = (state as any).dealer_data || { panic_level: 'NORMAL', signals: [] }

  const panicClr = d.panic_level === 'EXTREME' ? 'text-red-400 border-red-500/40 bg-red-950/20'
    : d.panic_level === 'HIGH' ? 'text-orange-400 border-orange-500/40 bg-orange-950/20'
    : d.panic_level === 'ELEVATED' ? 'text-yellow-400 border-yellow-500/30 bg-yellow-950/15'
    : 'text-gray-400 border-gray-700 bg-gray-900/30'

  return (
    <div className="h-full flex flex-col bg-[#060608] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-[#0a0a14] border-b border-purple-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center text-[10px] font-black text-black">DP</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.15em] text-purple-400">DEALER POSITIONS</h1>
              <p className="text-[9px] text-purple-800">Panic Velocity • Gamma Squeeze • Delta Reconstruction</p>
            </div>
          </div>
          <div className="text-[11px] font-mono text-gray-500">
            SPOT <span className="text-white font-bold">{d.spot?.toLocaleString('en-IN') || '—'}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* 1. PANIC VELOCITY */}
        <div className={`border rounded-xl p-4 ${panicClr}`}>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] uppercase tracking-widest font-bold opacity-80">Dealer Panic Velocity</p>
            <div className="flex items-center gap-2">
              {d.panic_stats && (
                <span className="text-[9px] font-mono text-gray-500">
                  CE:{d.panic_stats.ce_events || 0} PE:{d.panic_stats.pe_events || 0}
                </span>
              )}
              <span className="text-sm font-black">{d.panic_level}</span>
            </div>
          </div>
          <p className="text-[11px] leading-relaxed mb-2">{d.panic_msg}</p>

          {/* Conclusion + Buyer Action */}
          {d.panic_conclusion && (
            <div className="bg-black/30 rounded-lg p-3 mb-3 space-y-2">
              <div>
                <p className="text-[8px] text-gray-600 uppercase font-bold">Conclusion</p>
                <p className="text-[10px] text-gray-300 leading-relaxed">{d.panic_conclusion}</p>
              </div>
              <div>
                <p className="text-[8px] text-gray-600 uppercase font-bold">Buyer Action</p>
                <p className={`text-[10px] font-bold leading-relaxed ${
                  d.panic_buyer_action?.includes('BUY CE') ? 'text-emerald-400' :
                  d.panic_buyer_action?.includes('BUY PE') ? 'text-red-400' :
                  d.panic_buyer_action?.includes('WAIT') ? 'text-yellow-400' : 'text-gray-400'
                }`}>{d.panic_buyer_action}</p>
              </div>
            </div>
          )}

          {/* Current Panic Events */}
          {d.panic_events?.length > 0 && (
            <div className="space-y-1.5 mb-3">
              <p className="text-[8px] text-gray-600 uppercase font-bold">Live Panic Events</p>
              {d.panic_events.map((p: any, i: number) => (
                <div key={i} className="flex items-center gap-2 bg-black/30 rounded-lg px-3 py-2 text-[10px] font-mono">
                  <span className="text-white font-bold w-16">{p.strike} {p.side}</span>
                  <span className={`px-1 py-0.5 rounded text-[8px] font-bold ${
                    p.level === 'EXTREME' ? 'bg-red-900/50 text-red-400' :
                    p.level === 'HIGH' ? 'bg-orange-900/50 text-orange-400' : 'bg-yellow-900/50 text-yellow-400'
                  }`}>{p.level}</span>
                  <span className="text-red-400 font-bold">{(p.velocity || 0).toLocaleString('en-IN')} OI/min</span>
                  {p.acceleration && <span className={`text-[9px] ${(p.acceleration || 0) < -5000 ? 'text-red-400' : 'text-gray-600'}`}>
                    {(p.acceleration || 0) < -5000 ? '⚡ ACCELERATING' : '→ steady'}
                  </span>}
                </div>
              ))}
            </div>
          )}

          {/* Panic History (persisted) */}
          {d.panic_history?.length > 0 && (
            <div>
              <p className="text-[8px] text-gray-600 uppercase font-bold mb-1">Panic Log (all events today)</p>
              <div className="max-h-32 overflow-y-auto space-y-0.5">
                {[...(d.panic_history || [])].reverse().map((p: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[9px] font-mono py-0.5 border-b border-gray-900/30 last:border-0">
                    <span className="text-gray-600 w-12">{p.time}</span>
                    <span className="text-white w-14">{p.strike} {p.side}</span>
                    <span className={`px-1 rounded text-[8px] ${
                      p.level === 'EXTREME' ? 'text-red-400' : p.level === 'HIGH' ? 'text-orange-400' : 'text-yellow-400'
                    }`}>{p.level}</span>
                    <span className="text-red-400">{(p.velocity || 0).toLocaleString('en-IN')} OI/min</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!d.panic_events || d.panic_events.length === 0) && (!d.panic_history || d.panic_history.length === 0) && (
            <p className="text-[9px] text-gray-700 italic">No panic detected — sellers comfortable</p>
          )}
        </div>

        {/* 2. GAMMA SQUEEZE */}
        <div className={`border rounded-xl p-4 ${
          d.squeeze_active ? 'border-pink-500/40 bg-pink-950/15' : 'border-gray-800 bg-gray-900/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <p className={`text-[9px] uppercase tracking-widest font-bold ${d.squeeze_active ? 'text-pink-400' : 'text-gray-500'}`}>
              Gamma Squeeze Detector
            </p>
            <span className={`text-[10px] font-bold ${d.squeeze_active ? 'text-pink-400' : 'text-gray-600'}`}>
              {d.squeeze_active ? `ACTIVE — ${d.squeeze_direction}` : 'INACTIVE'}
            </span>
          </div>
          {d.squeeze_active ? (
            <p className="text-[11px] text-pink-300/80 leading-relaxed">{d.squeeze_detail}</p>
          ) : (
            <p className="text-[10px] text-gray-600">No squeeze. Gamma concentration: {((d.gamma_concentration || 0) * 100).toFixed(0)}% (need 60%+).</p>
          )}
          <div className="grid grid-cols-3 gap-3 mt-3 text-center text-[10px] font-mono">
            <div><p className="text-gray-600">CE GEX</p><p className="text-emerald-400 font-bold">{(d.ce_gex || 0).toLocaleString('en-IN')}</p></div>
            <div><p className="text-gray-600">PE GEX</p><p className="text-red-400 font-bold">{(d.pe_gex || 0).toLocaleString('en-IN')}</p></div>
            <div><p className="text-gray-600">NET GEX</p><p className={`font-bold ${(d.net_gex || 0) < 0 ? 'text-emerald-400' : 'text-red-400'}`}>{(d.net_gex || 0).toLocaleString('en-IN')}</p></div>
          </div>
        </div>

        {/* 3. DEALER DELTA — DETAILED */}
        <div className={`border rounded-xl p-4 ${
          d.delta_flip ? 'border-yellow-500/40 bg-yellow-950/15 animate-pulse' :
          d.stance_color === 'green' ? 'border-emerald-800/30 bg-emerald-950/10' :
          d.stance_color === 'red' ? 'border-red-800/30 bg-red-950/10' :
          'border-gray-800 bg-gray-900/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] text-yellow-400 uppercase tracking-widest font-bold">Dealer Delta Position</p>
            <div className="text-right">
              <span className={`text-lg font-black font-mono ${
                (d.net_dealer_delta || 0) > 0 ? 'text-emerald-400' : (d.net_dealer_delta || 0) < 0 ? 'text-red-400' : 'text-gray-500'
              }`}>{((d.net_dealer_delta || 0) / 1000).toFixed(0)}K</span>
              <p className={`text-[9px] font-bold ${d.stance_color === 'green' ? 'text-emerald-500' : d.stance_color === 'red' ? 'text-red-500' : 'text-gray-500'}`}>
                {d.dealer_stance}
              </p>
            </div>
          </div>

          {/* Scenario Explanation */}
          {d.delta_scenario && (
            <div className="bg-black/30 rounded-lg p-3 mb-3 space-y-2">
              <div>
                <p className="text-[8px] text-yellow-600 uppercase font-bold">What's Happening</p>
                <p className="text-[10px] text-gray-300 leading-relaxed">{d.delta_scenario}</p>
              </div>
              <div>
                <p className="text-[8px] text-yellow-600 uppercase font-bold">What It Means For Buyer</p>
                <p className={`text-[10px] font-semibold leading-relaxed ${
                  d.stance_color === 'green' ? 'text-emerald-400' : d.stance_color === 'red' ? 'text-red-400' : 'text-gray-400'
                }`}>{d.delta_what_it_means}</p>
              </div>
            </div>
          )}

          {/* Delta Trend */}
          {d.delta_trend && d.delta_trend !== 'STABLE' && (
            <div className={`text-[10px] px-3 py-1.5 rounded-lg mb-3 ${
              d.delta_trend === 'SHIFTING LONG' ? 'bg-emerald-950/20 text-emerald-400' :
              d.delta_trend === 'SHIFTING SHORT' ? 'bg-red-950/20 text-red-400' : 'bg-gray-900/30 text-gray-400'
            }`}>
              <span className="font-bold">{d.delta_trend}:</span> {d.delta_trend_detail}
            </div>
          )}

          {/* Delta Flip Alert */}
          {d.delta_flip && (
            <div className="border-2 border-yellow-500/50 bg-yellow-950/30 rounded-lg p-3 my-2">
              <p className="text-yellow-300 font-bold text-sm">⚡ {d.flip_direction}</p>
              <p className="text-[10px] text-yellow-400/80">{d.flip_detail}</p>
            </div>
          )}

          {/* Delta Breakdown — top strikes */}
          {d.delta_breakdown?.length > 0 && (
            <div className="mt-3">
              <p className="text-[8px] text-gray-600 uppercase mb-1">Top Delta Positions By Strike</p>
              <div className="space-y-0.5">
                {d.delta_breakdown.slice(0, 6).map((dd: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                    <span className="text-white w-14">{dd.strike} {dd.side}</span>
                    <span className="text-gray-600 w-10">δ{dd.delta}</span>
                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className={`h-full ${dd.dealer_delta > 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                           style={{ width: `${Math.min(100, Math.abs(dd.dealer_delta) / Math.max(Math.abs(d.net_dealer_delta || 1), 1) * 100)}%` }} />
                    </div>
                    <span className={`w-16 text-right ${dd.dealer_delta > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {(dd.dealer_delta / 1000).toFixed(0)}K
                    </span>
                    <span className="text-gray-600 text-[9px] w-12">{dd.direction}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* SIGNALS */}
        {d.signals?.length > 0 && (
          <div className="border border-purple-500/30 bg-purple-950/15 rounded-xl p-4">
            <p className="text-[9px] text-purple-400 uppercase tracking-widest font-bold mb-2">Dealer-Derived Signals</p>
            {d.signals.map((sig: any, i: number) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-800/30 last:border-0">
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  sig.conviction === 'MAXIMUM' ? 'bg-cyan-900/40 text-cyan-400' :
                  sig.conviction === 'HIGH' ? 'bg-emerald-900/40 text-emerald-400' :
                  'bg-yellow-900/40 text-yellow-400'
                }`}>{sig.signal}</span>
                <span className="text-[8px] text-purple-500 font-bold">{sig.source}</span>
                <span className="text-[10px] text-gray-400 flex-1">{sig.reason?.slice(0, 80)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Legend */}
        <div className="border border-gray-800 rounded-xl p-2 text-[8px] text-gray-600 grid grid-cols-3 gap-2">
          <span>Panic = how fast sellers cover (OI/min)</span>
          <span>Gamma Squeeze = forced dealer buying loop</span>
          <span>Delta Flip = dealer reversal = strongest signal</span>
        </div>
      </div>
    </div>
  )
}
