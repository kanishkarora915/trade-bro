import { useState } from 'react'

const STANCE_COLORS: Record<string, string> = {
  green: 'text-emerald-400 border-emerald-500/30 bg-emerald-950/20',
  red: 'text-red-400 border-red-500/30 bg-red-950/20',
  gray: 'text-gray-400 border-gray-700 bg-gray-900/30',
}

const ACTION_BADGES: Record<string, { bg: string; text: string }> = {
  'SHORT BUILD': { bg: 'bg-red-500/20', text: 'text-red-400' },
  'SHORT COVER': { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
  'LONG BUILD': { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  'LONG UNWIND': { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  'NEUTRAL': { bg: 'bg-gray-800', text: 'text-gray-500' },
}

function StrikeRow({ s }: { s: any }) {
  const badge = ACTION_BADGES[s.action] || ACTION_BADGES.NEUTRAL
  return (
    <tr className="border-b border-gray-900/50 hover:bg-gray-900/20 text-[10px] font-mono">
      <td className="py-1.5 font-bold text-white">{s.strike} <span className={s.side === 'CE' ? 'text-emerald-500' : 'text-red-500'}>{s.side}</span></td>
      <td><span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${badge.bg} ${badge.text}`}>{s.action}</span></td>
      <td className="text-right text-white">{s.ltp}</td>
      <td className={`text-right font-bold ${s.oi_chg > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
        {s.oi_chg > 0 ? '+' : ''}{(s.oi_chg || 0).toLocaleString('en-IN')}
      </td>
      <td className="text-right text-gray-400">{(s.oi || 0).toLocaleString('en-IN')}</td>
      <td className="text-right text-gray-400">{(s.volume || 0).toLocaleString('en-IN')}</td>
      <td className="text-right">
        <div className="flex items-center justify-end gap-1">
          <div className="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
            <div className="bg-emerald-500" style={{ width: `${s.buy_pct}%` }} />
            <div className="bg-red-500 flex-1" />
          </div>
          <span className="text-gray-500 w-8">{s.sell_pct?.toFixed(0)}%S</span>
        </div>
      </td>
    </tr>
  )
}

function ActivitySection({ title, items, color, icon }: { title: string; items: any[]; color: string; icon: string }) {
  if (!items?.length) return null
  return (
    <div className={`border rounded-xl p-3 ${color === 'green' ? 'border-emerald-800/30 bg-emerald-950/10' : color === 'red' ? 'border-red-800/30 bg-red-950/10' : 'border-yellow-800/30 bg-yellow-950/10'}`}>
      <p className={`text-[9px] uppercase tracking-widest font-bold mb-2 ${color === 'green' ? 'text-emerald-500' : color === 'red' ? 'text-red-500' : 'text-yellow-500'}`}>
        {icon} {title} ({items.length})
      </p>
      {items.map((item: any, i: number) => (
        <div key={i} className="flex items-start gap-2 py-1.5 border-b border-gray-800/30 last:border-0 text-[10px]">
          <span className={`font-mono font-bold shrink-0 ${color === 'green' ? 'text-emerald-400' : color === 'red' ? 'text-red-400' : 'text-yellow-400'}`}>
            {item.strike} {item.side}
          </span>
          <span className="text-gray-400 flex-1">{item.detail}</span>
          <span className={`shrink-0 text-[9px] px-1.5 py-0.5 rounded font-bold ${
            item.intensity === 'HEAVY' ? 'bg-red-900/40 text-red-400' :
            item.intensity === 'MODERATE' ? 'bg-yellow-900/40 text-yellow-400' :
            'bg-gray-800 text-gray-500'
          }`}>{item.intensity || item.threat_level || ''}</span>
        </div>
      ))}
    </div>
  )
}

export default function SellerFootprint({ state }: { state: any }) {
  const sf = (state as any).seller_footprint || { market_stance: 'Loading...', buyer_signals: [], strike_data: [] }
  const [showAll, setShowAll] = useState(false)
  const stanceColor = STANCE_COLORS[sf.stance_color] || STANCE_COLORS.gray

  return (
    <div className="h-full flex flex-col bg-[#080808] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-gray-900/60 border-b border-gray-700 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-orange-500 rounded-lg flex items-center justify-center text-[10px] font-black text-black">SF</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.15em] text-orange-400">SELLER FOOTPRINT</h1>
              <p className="text-[9px] text-orange-800">Track sellers to find buyer edge — OI + Price + Flow analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono">
            <span className="text-gray-500">SPOT <span className="text-white font-bold">{sf.spot?.toLocaleString('en-IN') || '—'}</span></span>
            <span className="text-gray-500">PCR <span className={`font-bold ${sf.pcr > 1 ? 'text-emerald-400' : sf.pcr < 0.7 ? 'text-red-400' : 'text-gray-300'}`}>{sf.pcr || '—'}</span></span>
            {sf.pcr_signal !== 'NEUTRAL' && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${sf.pcr_signal === 'OVERSOLD' ? 'bg-emerald-900/40 text-emerald-400' : 'bg-red-900/40 text-red-400'}`}>{sf.pcr_signal}</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Market Stance */}
        <div className={`border rounded-xl p-4 ${stanceColor}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[9px] uppercase tracking-widest opacity-60 mb-1">Seller Stance</p>
              <p className="text-lg font-black">{sf.market_stance}</p>
            </div>
            <div className="text-right text-[10px] font-mono">
              <div className="flex gap-4">
                <div>
                  <p className="text-gray-600">CE OI Chg</p>
                  <p className={`font-bold ${(sf.total_ce_oi_chg || 0) > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(sf.total_ce_oi_chg || 0) > 0 ? '+' : ''}{(sf.total_ce_oi_chg || 0).toLocaleString('en-IN')}
                  </p>
                </div>
                <div>
                  <p className="text-gray-600">PE OI Chg</p>
                  <p className={`font-bold ${(sf.total_pe_oi_chg || 0) > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(sf.total_pe_oi_chg || 0) > 0 ? '+' : ''}{(sf.total_pe_oi_chg || 0).toLocaleString('en-IN')}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Seller count summary */}
          <div className="grid grid-cols-4 gap-2 mt-3 text-center text-[9px]">
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-red-400 font-bold text-sm">{sf.ce_selling_strikes || 0}</p>
              <p className="text-gray-600">CE Writing</p>
            </div>
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-red-400 font-bold text-sm">{sf.pe_selling_strikes || 0}</p>
              <p className="text-gray-600">PE Writing</p>
            </div>
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-emerald-400 font-bold text-sm">{sf.ce_covering_strikes || 0}</p>
              <p className="text-gray-600">CE Covering</p>
            </div>
            <div className="bg-black/20 rounded-lg p-2">
              <p className="text-emerald-400 font-bold text-sm">{sf.pe_covering_strikes || 0}</p>
              <p className="text-gray-600">PE Covering</p>
            </div>
          </div>

          {/* Walls */}
          {(sf.ce_wall || sf.pe_wall) && (
            <div className="flex gap-4 mt-3 text-[10px] font-mono">
              {sf.ce_wall && <span className="text-red-400">CE Wall: {sf.ce_wall.strike} ({(sf.ce_wall.oi || 0).toLocaleString('en-IN')} OI) = Resistance</span>}
              {sf.pe_wall && <span className="text-emerald-400">PE Wall: {sf.pe_wall.strike} ({(sf.pe_wall.oi || 0).toLocaleString('en-IN')} OI) = Support</span>}
            </div>
          )}
        </div>

        {/* Buyer Signals from Seller Activity */}
        {sf.buyer_signals?.length > 0 && (
          <div className="border border-orange-800/30 bg-orange-950/10 rounded-xl p-4">
            <p className="text-[9px] text-orange-400 uppercase tracking-widest font-bold mb-2">Buyer Signals (from seller activity)</p>
            {sf.buyer_signals.map((sig: any, i: number) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-800/30 last:border-0">
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                  sig.type === 'bullish' ? 'bg-emerald-900/40 text-emerald-400' :
                  sig.type === 'bearish' ? 'bg-red-900/40 text-red-400' :
                  'bg-yellow-900/40 text-yellow-400'
                }`}>{sig.signal}</span>
                <span className="text-[10px] text-gray-400 flex-1">{sig.reason}</span>
                <span className={`text-[9px] font-bold ${sig.conviction === 'HIGH' ? 'text-emerald-400' : 'text-yellow-400'}`}>{sig.conviction}</span>
              </div>
            ))}
          </div>
        )}

        {/* Seller Activity Sections */}
        <div className="grid grid-cols-2 gap-3">
          <ActivitySection title="CE Short Build (Resistance)" items={sf.ce_short_build} color="red" icon="🔴" />
          <ActivitySection title="PE Short Build (Support)" items={sf.pe_short_build} color="red" icon="🔴" />
          <ActivitySection title="CE Short Cover (Bullish!)" items={sf.ce_short_cover} color="green" icon="🟢" />
          <ActivitySection title="PE Short Cover (Bearish)" items={sf.pe_short_cover} color="green" icon="🟢" />
        </div>

        {/* Sudden Entries + Slow Injections */}
        <ActivitySection title="Sudden Seller Entries" items={sf.sudden_entries} color="yellow" icon="⚡" />
        <ActivitySection title="Slow OI Injection (Stealth Sellers)" items={sf.slow_injections} color="yellow" icon="🐌" />

        {/* Full Strike Table */}
        <div className="border border-gray-800 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">All Active Strikes (by OI Change)</p>
            <button onClick={() => setShowAll(!showAll)} className="text-[9px] text-orange-400 hover:text-orange-300">{showAll ? 'Show Less' : 'Show All'}</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="text-[9px] text-gray-600 border-b border-gray-800">
                <tr>
                  <th className="text-left py-1">Strike</th>
                  <th className="text-left">Action</th>
                  <th className="text-right">LTP</th>
                  <th className="text-right">OI Chg</th>
                  <th className="text-right">OI</th>
                  <th className="text-right">Vol</th>
                  <th className="text-right">Sell%</th>
                </tr>
              </thead>
              <tbody>
                {(sf.strike_data || []).slice(0, showAll ? 20 : 8).map((s: any, i: number) => (
                  <StrikeRow key={i} s={s} />
                ))}
                {(!sf.strike_data || sf.strike_data.length === 0) && (
                  <tr><td colSpan={7} className="text-center py-4 text-gray-700 text-[10px] italic">No strike data — market closed or no chain</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* OI + Price Matrix Legend */}
        <div className="border border-gray-800 rounded-xl p-3">
          <p className="text-[9px] text-gray-500 uppercase tracking-widest font-bold mb-2">OI + Price Matrix (How to Read)</p>
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div className="flex items-center gap-2"><span className="text-red-400 font-bold">SHORT BUILD</span><span className="text-gray-600">OI UP + Price DOWN = Sellers entering</span></div>
            <div className="flex items-center gap-2"><span className="text-emerald-400 font-bold">SHORT COVER</span><span className="text-gray-600">OI DOWN + Price UP = Sellers exiting = BUY!</span></div>
            <div className="flex items-center gap-2"><span className="text-blue-400 font-bold">LONG BUILD</span><span className="text-gray-600">OI UP + Price UP = Buyers entering</span></div>
            <div className="flex items-center gap-2"><span className="text-yellow-400 font-bold">LONG UNWIND</span><span className="text-gray-600">OI DOWN + Price DOWN = Buyers exiting</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}
