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

export default function App() {
  const { step, session, error, loading, verifyLicense, setKiteCredentials, logout } = useSession()
  const sessionId = step === 'authenticated' && session ? session.session_id : null
  const { state, connected, latency, switchIndex } = useWebSocket(sessionId)
  useAlerts(state.confluence)

  const [selectedDetector, setSelectedDetector] = useState<DetectorResult | null>(null)
  const [showChain, setShowChain] = useState(false)

  if (loading && step !== 'kite_credentials') {
    return (
      <div className="min-h-screen bg-tb-bg flex items-center justify-center">
        <div className="text-center animate-slide-up">
          <div className="w-10 h-10 border-3 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-4" />
          <p className="text-tb-muted text-sm">Authenticating with Zerodha...</p>
        </div>
      </div>
    )
  }

  if (step === 'license') return <LicensePage onVerify={verifyLicense} error={error} loading={loading} />
  if (step === 'kite_credentials') return <KiteLoginPage userName={session?.user_name || ''} error={error} loading={loading} onSetCredentials={setKiteCredentials} onLogout={logout} />

  const flash = state.confluence.score >= 86 ? 'flash-red' : state.confluence.score >= 76 ? 'flash-green' : ''

  return (
    <div className={`h-screen flex flex-col bg-tb-bg overflow-hidden ${flash}`}>
      {/* Top bar */}
      <TopBar spot={state.spot} atm={state.atm} connected={connected} latency={latency} userName={session?.user_name || ''} onLogout={logout} />

      {/* Index tabs + Chain button */}
      <div className="shrink-0 flex items-center justify-between px-4 py-1.5 bg-tb-card/30 border-b border-tb-border">
        <IndexTabs active={state.active_index || 'NIFTY'} spots={state.spots || {}} onSwitch={switchIndex} />
        <button onClick={() => setShowChain(true)}
          className="text-[10px] font-bold text-neon-cyan border border-neon-cyan/30 px-3 py-1 rounded-lg hover:bg-neon-cyan/10 transition-all">
          Full Chain View
        </button>
      </div>

      {/* Error banner */}
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
          <BrainDashboard confluence={state.confluence} brain={state.brain} spot={state.spot} />
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
