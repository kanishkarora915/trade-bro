export default function SellerFootprint({ state }: { state: any }) {
  const sf = (state as any).seller_footprint || { stance: 'Loading...', signals: [], flash_alerts: [], ce_activity: [], pe_activity: [] }

  const stanceClr = sf.stance_color === 'green' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-950/20'
    : sf.stance_color === 'red' ? 'text-red-400 border-red-500/30 bg-red-950/20'
    : sf.stance_color === 'yellow' ? 'text-yellow-400 border-yellow-500/30 bg-yellow-950/20'
    : 'text-gray-400 border-gray-700 bg-gray-900/30'

  return (
    <div className="h-full flex flex-col bg-[#080808] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-gray-900/60 border-b border-orange-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-500 rounded-lg flex items-center justify-center text-[10px] font-black text-black">SF</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.15em] text-orange-400">SELLER FOOTPRINT</h1>
              <p className="text-[9px] text-orange-800">Real-time OI tracking — every seller move tracked, cumulative positions mapped</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono">
            <span className="text-gray-500">SPOT <span className="text-white font-bold">{sf.spot?.toLocaleString('en-IN') || '—'}</span></span>
            <span className="text-gray-500">PCR <span className={`font-bold ${sf.pcr > 1 ? 'text-emerald-400' : sf.pcr < 0.7 ? 'text-red-400' : 'text-gray-300'}`}>{sf.pcr || '—'}</span></span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Flash Alerts — ALWAYS on top */}
        {sf.flash_alerts?.length > 0 && (
          <div className="space-y-1.5">
            {sf.flash_alerts.map((alert: any, i: number) => (
              <div key={i} className={`border rounded-xl px-4 py-2.5 flex items-center gap-3 animate-pulse ${
                alert.type === 'danger' ? 'border-red-500/50 bg-red-950/30' : 'border-yellow-500/50 bg-yellow-950/30'
              }`}>
                <span className="text-lg">{alert.type === 'danger' ? '🚨' : '⚠️'}</span>
                <div className="flex-1">
                  <p className={`text-[11px] font-bold ${alert.type === 'danger' ? 'text-red-400' : 'text-yellow-400'}`}>{alert.msg}</p>
                  <p className="text-[9px] text-gray-500">{alert.time}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Market Stance */}
        <div className={`border rounded-xl p-4 ${stanceClr}`}>
          <p className="text-[9px] uppercase tracking-widest opacity-60 mb-1">Seller Stance</p>
          <p className="text-lg font-black">{sf.stance}</p>

          {/* OI Flow Summary */}
          <div className="grid grid-cols-4 gap-3 mt-3 text-center">
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-red-400 font-black text-sm font-mono">{((sf.ce_oi_added || 0) / 1000).toFixed(0)}K</p>
              <p className="text-[8px] text-gray-600">CE Writing</p>
            </div>
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-emerald-400 font-black text-sm font-mono">{((sf.ce_oi_removed || 0) / 1000).toFixed(0)}K</p>
              <p className="text-[8px] text-gray-600">CE Covering</p>
            </div>
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-red-400 font-black text-sm font-mono">{((sf.pe_oi_added || 0) / 1000).toFixed(0)}K</p>
              <p className="text-[8px] text-gray-600">PE Writing</p>
            </div>
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-emerald-400 font-black text-sm font-mono">{((sf.pe_oi_removed || 0) / 1000).toFixed(0)}K</p>
              <p className="text-[8px] text-gray-600">PE Covering</p>
            </div>
          </div>

          {/* Walls */}
          <div className="flex gap-4 mt-3 text-[10px] font-mono">
            {sf.max_ce_wall && <span className="text-red-400">CE Wall: {sf.max_ce_wall.strike} (OI +{(sf.max_ce_wall.oi_chg || 0).toLocaleString('en-IN')}) = Resistance</span>}
            {sf.max_pe_wall && <span className="text-emerald-400">PE Wall: {sf.max_pe_wall.strike} (OI +{(sf.max_pe_wall.oi_chg || 0).toLocaleString('en-IN')}) = Support</span>}
          </div>
        </div>

        {/* BUY Signals */}
        {sf.signals?.length > 0 && (
          <div className="space-y-2">
            {sf.signals.map((sig: any, i: number) => (
              <div key={i} className={`border-2 rounded-2xl p-4 ${
                sig.type === 'bullish' ? 'border-emerald-500/40 bg-emerald-950/20' :
                sig.type === 'bearish' ? 'border-red-500/40 bg-red-950/20' :
                'border-yellow-500/40 bg-yellow-950/20'
              }`}>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-sm font-black ${sig.type === 'bullish' ? 'text-emerald-400' : sig.type === 'bearish' ? 'text-red-400' : 'text-yellow-400'}`}>
                    {sig.signal === 'AVOID CE' ? '⛔' : sig.type === 'bullish' ? '▲' : '▼'} {sig.signal}
                  </span>
                  <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold ${
                    sig.conviction === 'HIGH' ? 'bg-emerald-900/40 text-emerald-400' : 'bg-yellow-900/40 text-yellow-400'
                  }`}>{sig.conviction}</span>
                </div>

                {sig.entry > 0 && (
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs font-mono mb-3">
                    <div className="flex justify-between"><span className="text-gray-500">STRIKE</span><span className="text-white font-bold">{sig.strike}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">ENTRY</span><span className="text-white font-bold">₹{sig.entry}</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">TARGET 1</span><span className="text-emerald-400">₹{sig.target1} (+50%)</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">TARGET 2</span><span className="text-emerald-400">₹{sig.target2} (+100%)</span></div>
                    <div className="flex justify-between"><span className="text-gray-500">STOP LOSS</span><span className="text-red-400 font-bold">₹{sig.stop_loss} (-40%)</span></div>
                  </div>
                )}

                <p className="text-[10px] text-gray-400 leading-relaxed mb-2">{sig.reason}</p>

                {sig.covering_strikes?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {sig.covering_strikes.map((s: string, j: number) => (
                      <span key={j} className="text-[9px] bg-black/30 text-gray-400 px-2 py-0.5 rounded-full font-mono">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {sf.signals?.length === 0 && (
          <div className="border border-gray-800 rounded-xl p-4 text-center">
            <p className="text-gray-500 text-sm">No buy signal yet</p>
            <p className="text-[10px] text-gray-700 mt-1">Waiting for sellers to show clear pattern — need 2+ strikes covering or 3+ strikes writing</p>
          </div>
        )}

        {/* CE Sellers + PE Sellers side by side */}
        <div className="grid grid-cols-2 gap-3">
          {/* CE Sellers (Call Writers) */}
          <div className="border border-red-900/30 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[9px] text-red-400 uppercase tracking-widest font-bold">CE Sellers (Call Writers)</p>
              <span className="text-[10px] font-mono text-gray-500">{sf.ce_writing_count || 0} writing, {sf.ce_covering_count || 0} covering</span>
            </div>
            {(sf.ce_activity || []).slice(0, 8).map((s: any, i: number) => (
              <div key={i} className="flex items-center gap-2 py-1.5 text-[10px] border-b border-gray-900/50 last:border-0 font-mono">
                <span className="text-white font-bold w-14">{s.strike}</span>
                <span className={`px-1 py-0.5 rounded text-[8px] font-bold ${
                  s.action === 'SELLER_WRITING' ? 'bg-red-900/40 text-red-400' :
                  s.action === 'SELLER_COVERING' ? 'bg-emerald-900/40 text-emerald-400' :
                  'bg-gray-800 text-gray-500'
                }`}>{s.action?.replace('SELLER_', '').replace('BUYER_', '')}</span>
                <span className={`ml-auto ${s.oi_chg > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {s.oi_chg > 0 ? '+' : ''}{(s.oi_chg / 1000).toFixed(0)}K
                </span>
              </div>
            ))}
            {(!sf.ce_activity || sf.ce_activity.length === 0) && <p className="text-[9px] text-gray-700 italic">No CE activity</p>}
          </div>

          {/* PE Sellers (Put Writers) */}
          <div className="border border-emerald-900/30 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[9px] text-emerald-400 uppercase tracking-widest font-bold">PE Sellers (Put Writers)</p>
              <span className="text-[10px] font-mono text-gray-500">{sf.pe_writing_count || 0} writing, {sf.pe_covering_count || 0} covering</span>
            </div>
            {(sf.pe_activity || []).slice(0, 8).map((s: any, i: number) => (
              <div key={i} className="flex items-center gap-2 py-1.5 text-[10px] border-b border-gray-900/50 last:border-0 font-mono">
                <span className="text-white font-bold w-14">{s.strike}</span>
                <span className={`px-1 py-0.5 rounded text-[8px] font-bold ${
                  s.action === 'SELLER_WRITING' ? 'bg-red-900/40 text-red-400' :
                  s.action === 'SELLER_COVERING' ? 'bg-emerald-900/40 text-emerald-400' :
                  'bg-gray-800 text-gray-500'
                }`}>{s.action?.replace('SELLER_', '').replace('BUYER_', '')}</span>
                <span className={`ml-auto ${s.oi_chg > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {s.oi_chg > 0 ? '+' : ''}{(s.oi_chg / 1000).toFixed(0)}K
                </span>
              </div>
            ))}
            {(!sf.pe_activity || sf.pe_activity.length === 0) && <p className="text-[9px] text-gray-700 italic">No PE activity</p>}
          </div>
        </div>

        {/* Legend */}
        <div className="border border-gray-800 rounded-xl p-3 text-[9px] text-gray-600">
          <div className="grid grid-cols-2 gap-1">
            <span><span className="text-red-400 font-bold">WRITING</span> = OI UP + Price DOWN = Seller entering</span>
            <span><span className="text-emerald-400 font-bold">COVERING</span> = OI DOWN + Price UP = Seller exiting = <span className="text-emerald-400">BUY signal</span></span>
            <span><span className="text-blue-400 font-bold">ENTERING</span> = OI UP + Price UP = Buyer building longs</span>
            <span><span className="text-yellow-400 font-bold">EXITING</span> = OI DOWN + Price DOWN = Buyer unwinding</span>
          </div>
        </div>
      </div>
    </div>
  )
}
