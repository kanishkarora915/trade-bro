import { useState, useEffect } from 'react'

export default function PaperTrade({ state }: { state: any }) {
  const pt = (state as any).paper_trade || { settings: {}, positions: [], closed_trades: [] }
  const [showSettings, setShowSettings] = useState(false)
  const [reportPeriod, setReportPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily')
  const [report, setReport] = useState<any>(null)
  const [capital, setCapital] = useState(pt.settings?.capital || 1000000)
  const [niftyLot, setNiftyLot] = useState(pt.settings?.lot_sizes?.NIFTY || 65)
  const [bnLot, setBnLot] = useState(pt.settings?.lot_sizes?.BANKNIFTY || 30)
  const [sensexLot, setSensexLot] = useState(pt.settings?.lot_sizes?.SENSEX || 20)

  const API = (import.meta as any).env?.VITE_API_URL || ''

  // Fetch report on period change
  useEffect(() => {
    fetch(`${API}/api/paper/report/${reportPeriod}`)
      .then(r => r.json()).then(setReport).catch(() => {})
  }, [reportPeriod])

  const saveSettings = () => {
    fetch(`${API}/api/paper/settings`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capital, lot_sizes: { NIFTY: niftyLot, BANKNIFTY: bnLot, SENSEX: sensexLot } })
    }).then(() => setShowSettings(false)).catch(() => {})
  }

  const exportCSV = () => {
    window.open(`${API}/api/paper/export/${reportPeriod}`, '_blank')
  }

  const pnlColor = (v: number) => v > 0 ? 'text-emerald-400' : v < 0 ? 'text-red-400' : 'text-gray-400'
  const r = report || {}

  return (
    <div className="h-full flex flex-col bg-[#050505] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-gradient-to-r from-[#0a100a] to-[#080808] border-b border-emerald-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-emerald-400 to-green-600 rounded-xl flex items-center justify-center text-[11px] font-black text-black">PT</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.2em] text-emerald-400">PAPER TRADE</h1>
              <p className="text-[9px] text-emerald-800">Live LTP tracking • Real math • No mock data</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={exportCSV} className="text-[10px] font-bold text-blue-400 border border-blue-500/30 px-3 py-1 rounded-lg hover:bg-blue-500/10">Export CSV</button>
            <button onClick={() => setShowSettings(!showSettings)} className="text-[10px] font-bold text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-lg hover:bg-emerald-500/10">Settings</button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Settings */}
        {showSettings && (
          <div className="border border-emerald-800/30 bg-emerald-950/10 rounded-xl p-4">
            <p className="text-[9px] text-emerald-500 uppercase tracking-widest font-bold mb-3">Settings (editable)</p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">Capital (₹)</label>
                <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">NIFTY Lot (1 lot = qty)</label>
                <input type="number" value={niftyLot} onChange={e => setNiftyLot(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">BANKNIFTY Lot (1 lot = qty)</label>
                <input type="number" value={bnLot} onChange={e => setBnLot(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
              <div>
                <label className="text-[9px] text-gray-500 block mb-1">SENSEX Lot (1 lot = qty)</label>
                <input type="number" value={sensexLot} onChange={e => setSensexLot(Number(e.target.value))}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm font-mono focus:border-emerald-500 focus:outline-none" />
              </div>
            </div>
            <button onClick={saveSettings} className="mt-3 w-full bg-emerald-600 hover:bg-emerald-500 text-black font-bold py-1.5 rounded-lg text-sm">Save</button>
          </div>
        )}

        {/* Capital Overview — REAL MATH */}
        <div className="grid grid-cols-5 gap-2">
          <div className="border border-gray-800 rounded-xl p-2.5 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Starting Capital</p>
            <p className="text-sm font-black text-white font-mono">₹{((pt.capital_total || 0) / 100000).toFixed(1)}L</p>
          </div>
          <div className="border border-gray-800 rounded-xl p-2.5 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Used</p>
            <p className="text-sm font-black text-yellow-400 font-mono">₹{((pt.capital_used || 0) / 1000).toFixed(0)}K</p>
          </div>
          <div className="border border-gray-800 rounded-xl p-2.5 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Available</p>
            <p className="text-sm font-black text-cyan-400 font-mono">₹{((pt.capital_available || 0) / 100000).toFixed(1)}L</p>
          </div>
          <div className={`border rounded-xl p-2.5 text-center ${(pt.total_pnl || 0) >= 0 ? 'border-emerald-800/30 bg-emerald-950/10' : 'border-red-800/30 bg-red-950/10'}`}>
            <p className="text-[8px] text-gray-600 uppercase">Net P&L</p>
            <p className={`text-sm font-black font-mono ${pnlColor(pt.total_pnl || 0)}`}>₹{(pt.total_pnl || 0).toLocaleString('en-IN')}</p>
          </div>
          <div className="border border-gray-800 rounded-xl p-2.5 text-center">
            <p className="text-[8px] text-gray-600 uppercase">Equity</p>
            <p className={`text-sm font-black font-mono ${pnlColor(pt.total_pnl || 0)}`}>₹{((pt.equity || 0) / 100000).toFixed(2)}L</p>
          </div>
        </div>

        {/* Period Tabs */}
        <div className="flex gap-1">
          {(['daily', 'weekly', 'monthly'] as const).map(p => (
            <button key={p} onClick={() => setReportPeriod(p)}
              className={`flex-1 text-[10px] font-bold py-2 rounded-lg transition-all ${
                reportPeriod === p ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'text-gray-500 border border-gray-800 hover:text-gray-300'
              }`}>
              {p === 'daily' ? 'Today' : p === 'weekly' ? 'This Week' : 'This Month'}
            </button>
          ))}
        </div>

        {/* P&L Report — FULL MATH */}
        {r.total_trades > 0 ? (
          <div className="border border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[9px] text-emerald-500 uppercase tracking-widest font-bold">{r.period_label} P&L Report</p>
              <span className={`text-lg font-black font-mono ${pnlColor(r.net_pnl || 0)}`}>
                {(r.net_pnl || 0) >= 0 ? '+' : ''}₹{(r.net_pnl || 0).toLocaleString('en-IN')}
              </span>
            </div>

            <div className="grid grid-cols-4 gap-3 text-center text-[10px] mb-3">
              <div className="bg-gray-900/50 rounded-lg p-2">
                <p className="text-gray-600">Trades</p><p className="text-white font-bold text-sm">{r.total_trades}</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-2">
                <p className="text-gray-600">Win Rate</p><p className="text-cyan-400 font-bold text-sm">{r.win_rate}%</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-2">
                <p className="text-gray-600">Profit Factor</p><p className={`font-bold text-sm ${(r.profit_factor || 0) >= 1.5 ? 'text-emerald-400' : 'text-yellow-400'}`}>{r.profit_factor}</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-2">
                <p className="text-gray-600">Expectancy</p><p className={`font-bold text-sm ${pnlColor(r.expectancy || 0)}`}>₹{(r.expectancy || 0).toLocaleString('en-IN')}</p>
              </div>
            </div>

            {/* Detailed P&L Math */}
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[10px] font-mono bg-black/30 rounded-lg p-3 mb-3">
              <div className="flex justify-between"><span className="text-gray-500">Gross Profit</span><span className="text-emerald-400">+₹{(r.gross_profit || 0).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Gross Loss</span><span className="text-red-400">₹{(r.gross_loss || 0).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Avg Win</span><span className="text-emerald-400">₹{(r.avg_win || 0).toLocaleString('en-IN')} ({r.avg_win_pct}%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Avg Loss</span><span className="text-red-400">₹{(r.avg_loss || 0).toLocaleString('en-IN')} ({r.avg_loss_pct}%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Max Drawdown</span><span className="text-red-400">₹{(r.max_drawdown || 0).toLocaleString('en-IN')} ({r.max_drawdown_pct}%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Capital Growth</span><span className={pnlColor(r.capital_growth || 0)}>{r.capital_growth_pct}%</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Win Streak</span><span className="text-emerald-400">{r.max_win_streak}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Loss Streak</span><span className="text-red-400">{r.max_loss_streak}</span></div>
              <div className="flex justify-between border-t border-gray-800 pt-1"><span className="text-gray-400 font-bold">Capital Start</span><span className="text-white">₹{(r.starting_capital || 0).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between border-t border-gray-800 pt-1"><span className="text-gray-400 font-bold">Capital Now</span><span className={`font-bold ${pnlColor(r.capital_growth || 0)}`}>₹{(r.capital_remaining || 0).toLocaleString('en-IN')}</span></div>
            </div>

            {/* Daily Breakdown (for weekly/monthly) */}
            {r.daily_pnls?.length > 1 && (
              <div className="mb-3">
                <p className="text-[8px] text-gray-600 uppercase mb-1">Daily Breakdown</p>
                <div className="space-y-0.5">
                  {r.daily_pnls.map((d: any, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-[10px] font-mono py-1 border-b border-gray-900/30 last:border-0">
                      <span className="text-gray-500 w-20">{d.date}</span>
                      <span className="text-white w-8">{d.trades}T</span>
                      <span className="text-emerald-400 w-8">{d.wins}W</span>
                      <span className="text-red-400 w-8">{d.losses}L</span>
                      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div className={`h-full ${d.net_pnl >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`}
                             style={{ width: `${Math.min(100, Math.abs(d.net_pnl) / Math.max(Math.abs(r.net_pnl || 1), 1) * 100)}%` }} />
                      </div>
                      <span className={`w-20 text-right font-bold ${pnlColor(d.net_pnl)}`}>
                        {d.net_pnl >= 0 ? '+' : ''}₹{d.net_pnl.toLocaleString('en-IN')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="border border-gray-800 rounded-xl p-4 text-center">
            <p className="text-gray-500 text-sm">No closed trades for {reportPeriod === 'daily' ? 'today' : reportPeriod === 'weekly' ? 'this week' : 'this month'}</p>
          </div>
        )}

        {/* Active Positions */}
        {pt.positions?.length > 0 && (
          <div className="border border-emerald-800/30 bg-emerald-950/5 rounded-xl p-4">
            <p className="text-[9px] text-emerald-500 uppercase tracking-widest font-bold mb-3">Active Positions (Live)</p>
            {pt.positions.map((pos: any, i: number) => (
              <div key={i} className={`border rounded-xl p-3 mb-2 ${(pos.pnl_pct || 0) >= 0 ? 'border-emerald-800/20 bg-emerald-950/10' : 'border-red-800/20 bg-red-950/10'}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-bold font-mono">{pos.strike}</span>
                    <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold ${pos.source === 'SNIPER' ? 'bg-yellow-900/40 text-yellow-400' : 'bg-cyan-900/40 text-cyan-400'}`}>{pos.source}</span>
                  </div>
                  <span className={`text-lg font-black font-mono ${pnlColor(pos.pnl_pct || 0)}`}>{(pos.pnl_pct || 0) >= 0 ? '+' : ''}{pos.pnl_pct}%</span>
                </div>
                <div className="grid grid-cols-4 gap-2 text-[10px] font-mono">
                  <div><span className="text-gray-600">Entry</span><br/><span className="text-white">₹{pos.entry_price}</span></div>
                  <div><span className="text-gray-600">LTP</span><br/><span className={pnlColor(pos.pnl_pct || 0)}>₹{pos.current_ltp}</span></div>
                  <div><span className="text-gray-600">P&L</span><br/><span className={pnlColor(pos.pnl_abs || 0)}>₹{(pos.pnl_abs || 0).toLocaleString('en-IN')}</span></div>
                  <div><span className="text-gray-600">Lots</span><br/><span className="text-white">{pos.lots} × {pos.lot_size} qty</span></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Lot Sizes Reference */}
        <div className="border border-gray-800 rounded-xl p-2 text-[8px] text-gray-600 flex justify-between">
          <span>NIFTY: 1 lot = {pt.settings?.lot_sizes?.NIFTY || 65} qty</span>
          <span>BANKNIFTY: 1 lot = {pt.settings?.lot_sizes?.BANKNIFTY || 30} qty</span>
          <span>SENSEX: 1 lot = {pt.settings?.lot_sizes?.SENSEX || 20} qty</span>
          <span>Capital: ₹{((pt.capital_total || 0) / 100000).toFixed(0)}L</span>
        </div>
      </div>
    </div>
  )
}
