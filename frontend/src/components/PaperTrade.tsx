import { useState } from 'react'

export default function PaperTrade({ state }: { state: any }) {
  const pt = (state as any).paper_trade || { settings: {}, positions: [], closed_trades: [] }
  const [showSettings, setShowSettings] = useState(false)
  const [capital, setCapital] = useState(pt.settings?.capital || 1000000)
  const [niftyLot, setNiftyLot] = useState(pt.settings?.lot_sizes?.NIFTY || 75)
  const [bnLot, setBnLot] = useState(pt.settings?.lot_sizes?.BANKNIFTY || 30)
  const [sensexLot, setSensexLot] = useState(pt.settings?.lot_sizes?.SENSEX || 20)

  const API = (import.meta as any).env?.VITE_API_URL || ''
  const saveSettings = () => {
    fetch(`${API}/api/paper/settings`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capital, lot_sizes: { NIFTY: niftyLot, BANKNIFTY: bnLot, SENSEX: sensexLot } })
    }).then(() => setShowSettings(false)).catch(() => {})
  }

  const pnlColor = (v: number) => v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-gray-400'

  return (
    <div className="h-full flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-gradient-to-r from-[#0a100a] to-[#080808] border-b border-emerald-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-emerald-400 to-green-600 rounded-xl flex items-center justify-center text-[11px] font-black text-black">PT</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.2em] text-emerald-400">PAPER TRADE</h1>
              <p className="text-[9px] text-emerald-800">Auto-fetch from Sniper + Command. Live LTP tracking. No real money.</p>
            </div>
          </div>
          <button onClick={() => setShowSettings(!showSettings)}
            className="text-[10px] font-bold text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-lg hover:bg-emerald-500/10">
            {showSettings ? 'Close Settings' : 'Settings'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Settings Panel */}
        {showSettings && (
          <div className="border border-emerald-800/30 bg-emerald-950/10 rounded-xl p-4">
            <p className="text-[9px] text-emerald-500 uppercase tracking-widest font-bold mb-3">Paper Trading Settings</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">Capital (₹)</label>
                <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">Max SL %</label>
                <input type="number" value={pt.settings?.max_sl_pct || 15} readOnly
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-gray-400 text-sm font-mono" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">NIFTY Lot Size</label>
                <input type="number" value={niftyLot} onChange={e => setNiftyLot(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">BANKNIFTY Lot Size</label>
                <input type="number" value={bnLot} onChange={e => setBnLot(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">SENSEX Lot Size</label>
                <input type="number" value={sensexLot} onChange={e => setSensexLot(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div className="flex items-end">
                <button onClick={saveSettings}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-black font-bold py-1.5 rounded-lg text-sm transition-all">
                  Save Settings
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Capital Overview */}
        <div className="grid grid-cols-4 gap-2">
          <div className="border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Capital</p>
            <p className="text-sm font-black text-white font-mono">₹{((pt.capital_total || 0) / 100000).toFixed(1)}L</p>
          </div>
          <div className="border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Used</p>
            <p className="text-sm font-black text-yellow-400 font-mono">₹{((pt.capital_used || 0) / 1000).toFixed(0)}K</p>
          </div>
          <div className="border border-gray-800 rounded-xl p-3 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Available</p>
            <p className="text-sm font-black text-emerald-400 font-mono">₹{((pt.capital_available || 0) / 100000).toFixed(1)}L</p>
          </div>
          <div className={`border rounded-xl p-3 text-center ${(pt.total_pnl || 0) >= 0 ? 'border-emerald-800/30 bg-emerald-950/10' : 'border-red-800/30 bg-red-950/10'}`}>
            <p className="text-[8px] text-gray-600 uppercase">Total P&L</p>
            <p className={`text-sm font-black font-mono ${pnlColor(pt.total_pnl || 0)}`}>
              {(pt.total_pnl || 0) >= 0 ? '+' : ''}₹{(pt.total_pnl || 0).toLocaleString('en-IN')}
            </p>
            <p className={`text-[9px] font-mono ${pnlColor(pt.total_pnl_pct || 0)}`}>{(pt.total_pnl_pct || 0) >= 0 ? '+' : ''}{pt.total_pnl_pct || 0}%</p>
          </div>
        </div>

        {/* Today's Stats */}
        <div className="grid grid-cols-5 gap-2 text-center text-[10px]">
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-gray-600">Trades</p><p className="text-white font-bold">{pt.trades_today || 0}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-gray-600">Wins</p><p className="text-emerald-400 font-bold">{pt.wins || 0}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-gray-600">Losses</p><p className="text-red-400 font-bold">{pt.losses || 0}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-gray-600">Win Rate</p><p className="text-cyan-400 font-bold">{pt.win_rate || 0}%</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2">
            <p className="text-gray-600">Open</p><p className="text-yellow-400 font-bold">{pt.positions_count || 0}</p>
          </div>
        </div>

        {/* Active Positions */}
        {pt.positions?.length > 0 && (
          <div className="border border-emerald-800/30 bg-emerald-950/5 rounded-xl p-4">
            <p className="text-[9px] text-emerald-500 uppercase tracking-widest font-bold mb-3">Active Positions (Live LTP)</p>
            {pt.positions.map((pos: any, i: number) => (
              <div key={i} className={`border rounded-xl p-3 mb-2 ${(pos.pnl_pct || 0) >= 0 ? 'border-emerald-800/20 bg-emerald-950/10' : 'border-red-800/20 bg-red-950/10'}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-bold text-sm font-mono">{pos.strike}</span>
                    <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${pos.source === 'SNIPER' ? 'bg-yellow-900/40 text-yellow-400' : 'bg-cyan-900/40 text-cyan-400'}`}>{pos.source}</span>
                    {pos.t1_hit && <span className="text-[8px] bg-emerald-900/40 text-emerald-400 px-1.5 py-0.5 rounded font-bold">T1 HIT</span>}
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-black font-mono ${pnlColor(pos.pnl_pct || 0)}`}>{(pos.pnl_pct || 0) >= 0 ? '+' : ''}{pos.pnl_pct}%</p>
                    <p className={`text-[10px] font-mono ${pnlColor(pos.pnl_abs || 0)}`}>₹{(pos.pnl_abs || 0).toLocaleString('en-IN')}</p>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-[10px] font-mono">
                  <div><span className="text-gray-600">Entry</span><br/><span className="text-white">₹{pos.entry_price}</span></div>
                  <div><span className="text-gray-600">LTP</span><br/><span className={pnlColor(pos.pnl_pct || 0)}>₹{pos.current_ltp}</span></div>
                  <div><span className="text-gray-600">SL</span><br/><span className="text-red-400">₹{pos.stop_loss}</span></div>
                  <div><span className="text-gray-600">Lots</span><br/><span className="text-white">{pos.lots} × {pos.lot_size}</span></div>
                </div>
                {/* Mini LTP sparkline */}
                {pos.ltp_history?.length > 2 && (
                  <div className="mt-2">
                    <svg width="100%" height="25" viewBox={`0 0 ${pos.ltp_history.length} 25`} preserveAspectRatio="none">
                      {(() => {
                        const prices = pos.ltp_history.map((h: any) => h.ltp)
                        const min = Math.min(...prices)
                        const max = Math.max(...prices)
                        const range = max - min || 1
                        const pts = prices.map((p: number, j: number) => `${j},${25 - ((p - min) / range) * 23 - 1}`).join(' ')
                        return <polyline points={pts} fill="none" stroke={pos.pnl_pct >= 0 ? '#10B981' : '#EF4444'} strokeWidth="1.5" />
                      })()}
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {pt.positions?.length === 0 && (
          <div className="border border-gray-800 rounded-xl p-4 text-center">
            <p className="text-gray-500 text-sm">No active positions</p>
            <p className="text-[10px] text-gray-700 mt-1">Waiting for Sniper/Command Center to generate a BUY signal...</p>
          </div>
        )}

        {/* Closed Trades Today */}
        {pt.closed_trades?.length > 0 && (
          <div className="border border-gray-800 rounded-xl p-3">
            <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold mb-2">Closed Trades Today</p>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] font-mono">
                <thead className="text-gray-600 border-b border-gray-800">
                  <tr>
                    <th className="text-left py-1">Strike</th>
                    <th className="text-right">Entry</th>
                    <th className="text-right">Exit</th>
                    <th className="text-right">P&L</th>
                    <th className="text-right">P&L ₹</th>
                    <th className="text-right">Hold</th>
                    <th className="text-left pl-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {[...(pt.closed_trades || [])].reverse().map((t: any, i: number) => (
                    <tr key={i} className="border-b border-gray-900/30 hover:bg-gray-900/20">
                      <td className="py-1.5 text-white font-bold">{t.strike}</td>
                      <td className="text-right text-gray-300">₹{t.entry_price}</td>
                      <td className="text-right text-gray-300">₹{t.exit_price}</td>
                      <td className={`text-right font-bold ${pnlColor(t.final_pnl_pct || 0)}`}>
                        {(t.final_pnl_pct || 0) > 0 ? '+' : ''}{t.final_pnl_pct}%
                      </td>
                      <td className={`text-right ${pnlColor(t.final_pnl_abs || 0)}`}>
                        ₹{(t.final_pnl_abs || 0).toLocaleString('en-IN')}
                      </td>
                      <td className="text-right text-gray-500">{t.hold_time_min}m</td>
                      <td className="pl-2 text-gray-500">{t.exit_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Equity info */}
        <div className="border border-gray-800 rounded-xl p-2 text-[8px] text-gray-600 flex justify-between">
          <span>Equity: ₹{((pt.equity || 0) / 100000).toFixed(2)}L</span>
          <span>Open P&L: ₹{(pt.open_pnl || 0).toLocaleString('en-IN')}</span>
          <span>Closed P&L: ₹{(pt.closed_pnl || 0).toLocaleString('en-IN')}</span>
          <span>Auto-fetch: Sniper + Command</span>
        </div>
      </div>
    </div>
  )
}
