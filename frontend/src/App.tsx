import { useState } from 'react'
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

export default function App() {
  const { step, session, error, loading, verifyLicense, setKiteCredentials, logout } = useSession()
  const sessionId = step === 'authenticated' && session ? session.session_id : null
  const { state, connected, latency, switchIndex, toggleVix } = useWebSocket(sessionId)
  useAlerts(state.confluence)

  const [selectedDetector, setSelectedDetector] = useState<DetectorResult | null>(null)
  const [showChain, setShowChain] = useState(false)
  const [activeTab, setActiveTab] = useState<'main' | 'flow'>('main')

  // Show spinner during Zerodha callback or any non-credentials loading
  if (step === 'kite_redirect' || (loading && step !== 'kite_credentials' && step !== 'license')) {
    return (
      <div className="min-h-screen bg-tb-bg flex items-center justify-center">
        <div className="text-center animate-slide-up">
          <div className="w-10 h-10 border-3 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-4" />
          <p className="text-tb-muted text-sm">Authenticating with Zerodha...</p>
          <p className="text-tb-muted/40 text-[10px] mt-2">Exchanging token with Kite API</p>
        </div>
      </div>
    )
  }

  if (step === 'license') return <LicensePage onVerify={verifyLicense} error={error} loading={loading} />
  if (step === 'kite_credentials') return <KiteLoginPage userName={session?.user_name || ''} error={error} loading={loading} onSetCredentials={setKiteCredentials} onLogout={logout} />

  // Authenticated but waiting for first data from WebSocket
  if (step === 'authenticated' && !connected && state.spot === 0) {
    return (
      <div className="min-h-screen bg-tb-bg flex items-center justify-center">
        <div className="text-center animate-slide-up">
          <div className="w-10 h-10 border-3 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neon-cyan text-sm font-semibold">Authenticated! Connecting to TRADE BRO...</p>
          <p className="text-tb-muted/50 text-[10px] mt-2">Loading option chain from Kite API (first load ~10s)</p>
          <button onClick={() => { localStorage.clear(); window.location.reload() }}
            className="mt-6 text-[10px] text-tb-muted hover:text-neon-red border border-tb-border px-3 py-1.5 rounded transition-all">
            Stuck? Click to re-login
          </button>
        </div>
      </div>
    )
  }

  // Flow Dashboard — 2nd screen
  if (activeTab === 'flow') {
    return <FlowDashboard state={state} onBack={() => setActiveTab('main')} />
  }

  const flash = state.confluence.score >= 86 ? 'flash-red' : state.confluence.score >= 76 ? 'flash-green' : ''

  return (
    <div className={`h-screen flex flex-col bg-tb-bg overflow-hidden ${flash}`}>
      {/* Top bar */}
      <TopBar spot={state.spot} atm={state.atm} connected={connected} latency={latency} userName={session?.user_name || ''} onLogout={logout} indiaVix={state.india_vix} vixEnabled={state.vix_enabled} onToggleVix={toggleVix} />

      {/* Index tabs + Chain button */}
      <div className="shrink-0 flex items-center justify-between px-4 py-1.5 bg-tb-card/30 border-b border-tb-border">
        <IndexTabs active={state.active_index || 'NIFTY'} spots={state.spots || {}} onSwitch={switchIndex} />
        <div className="flex items-center gap-2">
          <button onClick={() => setActiveTab('flow')}
            className="text-[10px] font-bold text-neon-purple border border-neon-purple/30 px-3 py-1 rounded-lg hover:bg-neon-purple/10 transition-all">
            Flow Dashboard →
          </button>
          <button onClick={() => setShowChain(true)}
            className="text-[10px] font-bold text-neon-cyan border border-neon-cyan/30 px-3 py-1 rounded-lg hover:bg-neon-cyan/10 transition-all">
            Full Chain View
          </button>
        </div>
      </div>

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

      {/* Detector Detail Modal */}
      {selectedDetector && (
        <DetectorDetail detector={selectedDetector} onClose={() => setSelectedDetector(null)} />
      )}

      {/* Full Chain Modal */}
      {showChain && (
        <StrikeDetail chain={state.chain_summary || []} atm={state.atm} onClose={() => setShowChain(false)} />
      )}
    </div>
  )
}
