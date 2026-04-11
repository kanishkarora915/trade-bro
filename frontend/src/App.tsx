import { useState, useEffect } from 'react'
import { useSession } from './hooks/useSession'
import { useWebSocket, DetectorResult } from './hooks/useWebSocket'
import { useAlerts } from './hooks/useAlerts'
import LicensePage from './pages/LicensePage'
import KiteLoginPage from './pages/KiteLoginPage'
import TopBar from './components/TopBar'
import IndexTabs from './components/IndexTabs'
import IndicatorsPanel from './components/IndicatorsPanel'
import StrikeHeatmap from './components/StrikeHeatmap'
import BrainDashboard from './components/BrainDashboard'
import AlertLog from './components/AlertLog'
import FlowTape from './components/FlowTape'
import DetectorDetail from './components/DetectorDetail'
import StrikeDetail from './components/StrikeDetail'
import FlowDashboard from './components/FlowDashboard'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import TimeframeDashboard from './components/TimeframeDashboard'
import CheckTrades from './components/CheckTrades'
import BobDashboard from './components/BobDashboard'
import VPINDashboard from './components/VPINDashboard'
import SellerFootprint from './components/SellerFootprint'
import CommandCenter from './components/CommandCenter'
import DealerPositions from './components/DealerPositions'

export default function App() {
  const { step, session, error, loading, verifyLicense, setKiteCredentials, logout } = useSession()
  const sessionId = step === 'authenticated' && session ? session.session_id : null
  const { state, connected, latency, switchIndex, toggleVix } = useWebSocket(sessionId)
  useAlerts(state.confluence)

  const [selectedDetector, setSelectedDetector] = useState<DetectorResult | null>(null)
  const [showChain, setShowChain] = useState(false)
  const [activeTab, setActiveTab] = useState<'main' | 'flow' | 'analytics' | 'timeframes' | 'check' | 'bob' | 'vpin' | 'sellers' | 'command' | 'dealer'>('command')
  const [expiries, setExpiries] = useState<string[]>([])
  const [selectedExpiry, setSelectedExpiry] = useState('')

  // Fetch expiry list when authenticated
  const API = import.meta.env.VITE_API_URL || ''
  useEffect(() => {
    if (!sessionId) return
    fetch(`${API}/api/expiries/${sessionId}`)
      .then(r => r.json())
      .then(d => {
        if (d.expiries) setExpiries(d.expiries)
        if (d.current) setSelectedExpiry(d.current)
      })
      .catch(() => {})
  }, [sessionId, state.active_index])

  const switchExpiry = (exp: string) => {
    setSelectedExpiry(exp)
    fetch(`${API}/api/expiry/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, expiry: exp })
    }).catch(() => {})
  }

  // Zerodha callback — NO spinner, just process silently in background
  // useSession handles the token exchange automatically

  if (step === 'license') return <LicensePage onVerify={verifyLicense} error={error} loading={loading} />
  if (step === 'kite_credentials') return <KiteLoginPage userName={session?.user_name || ''} error={error} loading={loading} onSetCredentials={setKiteCredentials} onLogout={logout} />

  // Authenticated but waiting for first data — show dashboard skeleton immediately, no blank screen
  const flash = state.confluence.score >= 86 ? 'flash-red' : state.confluence.score >= 76 ? 'flash-green' : ''

  // Tab config
  const TABS = [
    { id: 'command' as const, label: 'Command', color: 'text-cyan-400', bg: 'bg-cyan-400/10' },
    { id: 'dealer' as const, label: 'Dealer', color: 'text-purple-400', bg: 'bg-purple-400/10' },
    { id: 'main' as const, label: 'Dashboard', color: 'text-white', bg: 'bg-white/10' },
    { id: 'flow' as const, label: 'Flow', color: 'text-neon-purple', bg: 'bg-neon-purple/10' },
    { id: 'analytics' as const, label: 'Analytics', color: 'text-neon-cyan', bg: 'bg-neon-cyan/10' },
    { id: 'timeframes' as const, label: 'Timeframes', color: 'text-neon-yellow', bg: 'bg-neon-yellow/10' },
    { id: 'check' as const, label: 'Check Trades', color: 'text-orange-400', bg: 'bg-orange-400/10' },
    { id: 'bob' as const, label: 'Bob', color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
    { id: 'vpin' as const, label: 'VPIN', color: 'text-blue-400', bg: 'bg-blue-400/10' },
    { id: 'sellers' as const, label: 'Sellers', color: 'text-orange-400', bg: 'bg-orange-400/10' },
  ]

  return (
    <div className={`h-screen flex flex-col bg-tb-bg overflow-hidden ${flash}`}>
      {/* PERSISTENT TOP BAR — always visible on ALL tabs */}
      <TopBar spot={state.spot} atm={state.atm} connected={connected} latency={latency} userName={session?.user_name || ''} onLogout={logout} indiaVix={state.india_vix} vixEnabled={state.vix_enabled} onToggleVix={toggleVix} />

      {/* PERSISTENT TAB NAV — click to switch, no back button needed */}
      <div className="shrink-0 flex items-center justify-between px-3 py-1 bg-tb-card/30 border-b border-tb-border">
        <div className="flex items-center gap-0.5">
          {/* Index tabs (NIFTY / BANKNIFTY / SENSEX) */}
          <IndexTabs active={state.active_index || 'NIFTY'} spots={state.spots || {}} onSwitch={switchIndex} />
          <span className="text-gray-700 mx-2">|</span>
          {/* Dashboard tabs */}
          {TABS.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={`text-[10px] font-bold px-3 py-1.5 rounded-lg transition-all ${
                activeTab === t.id
                  ? `${t.bg} ${t.color} border border-current`
                  : 'text-gray-500 hover:text-gray-300 border border-transparent'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {expiries.length > 0 && (
            <select
              value={selectedExpiry}
              onChange={e => switchExpiry(e.target.value)}
              className="text-[10px] font-bold font-mono bg-tb-bg text-neon-yellow border border-neon-yellow/30 px-2 py-1 rounded-lg cursor-pointer focus:outline-none focus:border-neon-yellow/60"
            >
              {expiries.map(e => (
                <option key={e} value={e}>{e}</option>
              ))}
            </select>
          )}
          <button onClick={() => setShowChain(true)}
            className="text-[10px] font-bold text-neon-cyan border border-neon-cyan/30 px-3 py-1 rounded-lg hover:bg-neon-cyan/10 transition-all">
            Full Chain View
          </button>
        </div>
      </div>

      {/* TAB CONTENT */}
      {activeTab === 'flow' ? (
        <FlowDashboard state={state} onBack={() => setActiveTab('main')} />
      ) : activeTab === 'analytics' ? (
        <AnalyticsDashboard state={state} onBack={() => setActiveTab('main')} sessionId={session?.session_id} />
      ) : activeTab === 'timeframes' ? (
        <TimeframeDashboard state={state} onBack={() => setActiveTab('main')} />
      ) : activeTab === 'check' ? (
        <CheckTrades state={state} />
      ) : activeTab === 'bob' ? (
        <BobDashboard state={state} />
      ) : activeTab === 'vpin' ? (
        <VPINDashboard state={state} />
      ) : activeTab === 'sellers' ? (
        <SellerFootprint state={state} />
      ) : activeTab === 'command' ? (
        <CommandCenter state={state} />
      ) : activeTab === 'dealer' ? (
        <DealerPositions state={state} />
      ) : (
      <>
      {/* MAIN DASHBOARD CONTENT */}

      {/* GAP & TREND BAR */}
      {(() => {
        const td = (state as any).trend_data?.[state.active_index || 'NIFTY']
        if (!td || !td.prev_close) return null
        const gapClr = td.gap_pct > 0.15 ? 'text-green-400' : td.gap_pct < -0.15 ? 'text-red-400' : 'text-gray-400'
        const trendClr = td.trend?.includes('UP') ? 'text-green-400' : td.trend?.includes('DOWN') ? 'text-red-400' : 'text-yellow-400'
        const dayClr = td.day_chg >= 0 ? 'text-green-400' : 'text-red-400'
        return (
          <div className="shrink-0 flex items-center gap-4 px-4 py-1 bg-gray-900/50 border-b border-tb-border text-[10px] font-mono overflow-x-auto">
            {/* Gap */}
            <div className="flex items-center gap-1.5">
              <span className={`font-extrabold text-[11px] px-1.5 py-0.5 rounded ${td.gap_pct > 0.15 ? 'bg-green-900/40' : td.gap_pct < -0.15 ? 'bg-red-900/40' : 'bg-gray-800'} ${gapClr}`}>
                {td.gap_type}
              </span>
              <span className={`font-bold ${gapClr}`}>{td.gap >= 0 ? '+' : ''}{td.gap.toFixed(1)} ({td.gap_pct >= 0 ? '+' : ''}{td.gap_pct.toFixed(2)}%)</span>
              {td.gap_filled && <span className="text-yellow-400 font-bold px-1 bg-yellow-900/30 rounded">GAP FILLED</span>}
            </div>
            <span className="text-gray-700">|</span>
            {/* Trend */}
            <div className="flex items-center gap-1.5">
              <span className={`font-extrabold ${trendClr}`}>
                {td.trend === 'TRENDING UP' ? '📈' : td.trend === 'TRENDING DOWN' ? '📉' : '➡️'} {td.trend}
              </span>
              {td.trend_strength > 0 && <span className="text-gray-500">({td.trend_strength.toFixed(0)}%)</span>}
            </div>
            <span className="text-gray-700">|</span>
            {/* Day Change */}
            <span className="text-gray-500">Day:</span>
            <span className={`font-bold ${dayClr}`}>{td.day_chg >= 0 ? '+' : ''}{td.day_chg.toFixed(1)} ({td.day_chg_pct >= 0 ? '+' : ''}{td.day_chg_pct.toFixed(2)}%)</span>
            <span className="text-gray-700">|</span>
            {/* OHLC */}
            <span className="text-gray-500">O:</span><span className="text-gray-300">{td.today_open?.toLocaleString('en-IN')}</span>
            <span className="text-gray-500">H:</span><span className="text-green-400 font-bold">{td.today_high?.toLocaleString('en-IN')}</span>
            <span className="text-gray-500">L:</span><span className="text-red-400 font-bold">{td.today_low?.toLocaleString('en-IN')}</span>
            <span className="text-gray-500">PC:</span><span className="text-gray-300">{td.prev_close?.toLocaleString('en-IN')}</span>
            <span className="text-gray-700">|</span>
            {/* Range */}
            <span className="text-gray-500">Range:</span><span className="text-cyan-400 font-bold">{td.day_range?.toFixed(1)} pts</span>
            {/* 5m Momentum */}
            {td.momentum_5m !== 0 && (
              <>
                <span className="text-gray-700">|</span>
                <span className="text-gray-500">5m:</span>
                <span className={`font-bold ${td.momentum_5m >= 0 ? 'text-green-400' : 'text-red-400'}`}>{td.momentum_5m >= 0 ? '+' : ''}{td.momentum_5m.toFixed(3)}%</span>
              </>
            )}
          </div>
        )
      })()}

      {/* Market status / Error banner */}
      {(() => {
        const now = new Date()
        const day = now.getDay()
        const h = now.getHours()
        const isWeekend = day === 0 || day === 6
        const isAfterHours = !isWeekend && (h < 9 || h >= 16)
        if (isWeekend || isAfterHours) return (
          <div className="shrink-0 bg-blue-950/30 border-b border-blue-900/30 px-4 py-1.5 text-[11px] text-neon-blue font-mono flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-neon-yellow rounded-full" />
            {isWeekend ? 'Market Closed — Weekend. Showing last trading day data.' : 'Market Closed — After Hours. Data from last session.'}
          </div>
        )
        return null
      })()}
      {state.error && (
        <div className="shrink-0 bg-red-950/30 border-b border-red-900/30 px-4 py-1.5 text-[11px] text-neon-red font-mono">
          API Error: {state.error}
        </div>
      )}

      {/* 5-Panel Grid */}
      <div className="flex-1 grid grid-cols-[260px_1fr_340px] grid-rows-[1fr_180px] gap-[1px] bg-tb-border overflow-hidden">
        {/* Left — Detectors (clickable) */}
        <div className="bg-tb-bg p-2 overflow-hidden">
          <IndicatorsPanel detectors={state.detectors} onDetectorClick={setSelectedDetector} />
        </div>

        {/* Center — Heatmap */}
        <div className="bg-tb-bg p-2 overflow-hidden">
          <StrikeHeatmap strikeMap={state.strike_map} atm={state.atm} />
        </div>

        {/* Right — Brain Dashboard */}
        <div className="bg-tb-bg p-3 overflow-y-auto row-span-2">
          <BrainDashboard
            confluence={state.confluence}
            brain={state.brain}
            spot={state.spot}
            aiAnalysis={state.ai_analysis}
            signalHistory={state.signal_history}
            lastSignal={state.last_signal}
            fiiDii={state.fii_dii}
            tickerActive={state.ticker_active}
            state={state}
          />
        </div>

        {/* Bottom Left — Flow Tape */}
        <div className="bg-tb-bg p-2 overflow-hidden">
          <FlowTape tape={state.flow_tape || []} />
        </div>

        {/* Bottom Center — Alert Log */}
        <div className="bg-tb-bg p-2 overflow-hidden">
          <AlertLog alerts={state.alert_log} />
        </div>
      </div>
      </>
      )}

      {/* Detector Detail Modal — works on all tabs */}
      {selectedDetector && (
        <DetectorDetail detector={selectedDetector} onClose={() => setSelectedDetector(null)} />
      )}

      {/* Full Chain Modal — works on all tabs */}
      {showChain && (
        <StrikeDetail chain={state.chain_summary || []} atm={state.atm} onClose={() => setShowChain(false)} />
      )}
    </div>
  )
}
