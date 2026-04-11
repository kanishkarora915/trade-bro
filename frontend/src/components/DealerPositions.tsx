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
            <span className="text-sm font-black">{d.panic_level}</span>
          </div>
          <p className="text-[11px] leading-relaxed mb-3">{d.panic_msg}</p>

          {d.panic_events?.length > 0 && (
            <div className="space-y-1.5">
              {d.panic_events.map((p: any, i: number) => (
                <div key={i} className="flex items-center gap-2 bg-black/30 rounded-lg px-3 py-2 text-[10px] font-mono">
                  <span className="text-white font-bold w-16">{p.strike} {p.side}</span>
                  <span className={`px-1 py-0.5 rounded text-[8px] font-bold ${
                    p.level === 'EXTREME' ? 'bg-red-900/50 text-red-400' :
                    p.level === 'HIGH' ? 'bg-orange-900/50 text-orange-400' : 'bg-yellow-900/50 text-yellow-400'
                  }`}>{p.level}</span>
                  <span className="text-red-400 font-bold">{(p.velocity || 0).toLocaleString('en-IN')} OI/min</span>
                  <span className="text-gray-500 flex-1 truncate">{p.detail}</span>
                </div>
              ))}
            </div>
          )}
          {(!d.panic_events || d.panic_events.length === 0) && (
            <p className="text-[9px] text-gray-700 italic">No panic detected — normal OI flow</p>
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
            <p className="text-[10px] text-gray-600">No gamma squeeze conditions. Concentration: {((d.gamma_concentration || 0) * 100).toFixed(0)}% (need 60%+).</p>
          )}

          <div className="grid grid-cols-3 gap-3 mt-3 text-center text-[10px] font-mono">
            <div>
              <p className="text-gray-600">CE GEX</p>
              <p className="text-emerald-400 font-bold">{(d.ce_gex || 0).toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p className="text-gray-600">PE GEX</p>
              <p className="text-red-400 font-bold">{(d.pe_gex || 0).toLocaleString('en-IN')}</p>
            </div>
            <div>
              <p className="text-gray-600">NET GEX</p>
              <p className={`font-bold ${(d.net_gex || 0) < 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {(d.net_gex || 0).toLocaleString('en-IN')}
              </p>
            </div>
          </div>
          {d.max_gamma_strike && (
            <p className="text-[9px] text-gray-600 mt-2 text-center">
              Max gamma at {d.max_gamma_strike.strike} {d.max_gamma_strike.side} (GEX: {(d.max_gamma_strike.gex || 0).toLocaleString('en-IN')})
            </p>
          )}
        </div>

        {/* 3. DEALER DELTA RECONSTRUCTION */}
        <div className={`border rounded-xl p-4 ${
          d.delta_flip ? 'border-yellow-500/40 bg-yellow-950/15 animate-pulse' :
          d.stance_color === 'green' ? 'border-emerald-800/30 bg-emerald-950/10' :
          d.stance_color === 'red' ? 'border-red-800/30 bg-red-950/10' :
          'border-gray-800 bg-gray-900/30'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] text-yellow-400 uppercase tracking-widest font-bold">Dealer Delta (Net Position)</p>
            <span className={`text-lg font-black font-mono ${
              (d.net_dealer_delta || 0) > 0 ? 'text-emerald-400' : (d.net_dealer_delta || 0) < 0 ? 'text-red-400' : 'text-gray-500'
            }`}>{((d.net_dealer_delta || 0) / 1000).toFixed(0)}K</span>
          </div>

          <p className={`text-[11px] leading-relaxed mb-2 ${
            d.stance_color === 'green' ? 'text-emerald-400' :
            d.stance_color === 'red' ? 'text-red-400' : 'text-gray-400'
          }`}>{d.dealer_stance}</p>

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
              <p className="text-[8px] text-gray-600 uppercase mb-1">Top Delta Positions</p>
              <div className="space-y-0.5">
                {d.delta_breakdown.slice(0, 6).map((dd: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                    <span className="text-white w-14">{dd.strike} {dd.side}</span>
                    <div className={`flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden`}>
                      <div className={`h-full ${dd.dealer_delta > 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                           style={{ width: `${Math.min(100, Math.abs(dd.dealer_delta) / (Math.abs(d.net_dealer_delta || 1)) * 100)}%` }} />
                    </div>
                    <span className={`w-16 text-right ${dd.dealer_delta > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {(dd.dealer_delta / 1000).toFixed(0)}K {dd.direction}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* SIGNALS from dealer analysis */}
        {d.signals?.length > 0 && (
          <div className="border border-purple-500/30 bg-purple-950/15 rounded-xl p-4">
            <p className="text-[9px] text-purple-400 uppercase tracking-widest font-bold mb-2">Dealer-Derived Buy Signals</p>
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
          <span>Panic Velocity = how fast sellers cover</span>
          <span>Gamma Squeeze = forced dealer buying loop</span>
          <span>Delta Flip = dealer position reversal = THE signal</span>
        </div>
      </div>
    </div>
  )
}
