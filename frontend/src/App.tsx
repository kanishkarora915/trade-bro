import { useSession } from './hooks/useSession'
import { useWebSocket } from './hooks/useWebSocket'
import { useAlerts } from './hooks/useAlerts'
import LicensePage from './pages/LicensePage'
import KiteLoginPage from './pages/KiteLoginPage'
import TopBar from './components/TopBar'
import IndicatorsPanel from './components/IndicatorsPanel'
import StrikeHeatmap from './components/StrikeHeatmap'
import BrainDashboard from './components/BrainDashboard'
import AlertLog from './components/AlertLog'

export default function App() {
  const { step, session, error, loading, loginUrl, verifyLicense, setKiteCredentials, handleCallback, logout } = useSession()
  const sessionId = step === 'authenticated' && session ? session.session_id : null
  const { state, connected, latency } = useWebSocket(sessionId)
  useAlerts(state.confluence)

  // License screen
  if (step === 'license') {
    return <LicensePage onVerify={verifyLicense} error={error} loading={loading} />
  }

  // Kite credentials / login
  if (step === 'kite_credentials' || step === 'kite_login') {
    return (
      <KiteLoginPage
        step={step}
        loginUrl={loginUrl}
        userName={session?.user_name || ''}
        error={error}
        loading={loading}
        onSetCredentials={setKiteCredentials}
        onCallback={handleCallback}
        onLogout={logout}
      />
    )
  }

  // Dashboard
  const flash = state.confluence.score >= 86 ? 'flash-red' : state.confluence.score >= 76 ? 'flash-green' : ''

  return (
    <div className={`h-screen flex flex-col bg-tb-bg overflow-hidden ${flash}`}>
      <TopBar
        spot={state.spot}
        atm={state.atm}
        connected={connected}
        latency={latency}
        userName={session?.user_name || ''}
        onLogout={logout}
      />

      {/* Error banner */}
      {state.error && (
        <div className="shrink-0 bg-red-950/30 border-b border-red-900/30 px-4 py-1.5 text-[11px] text-neon-red font-mono">
          API Error: {state.error}
        </div>
      )}

      {/* 4-Panel Grid */}
      <div className="flex-1 grid grid-cols-[280px_1fr_380px] grid-rows-[1fr_150px] gap-[1px] bg-tb-border overflow-hidden">
        {/* Left — Detectors */}
        <div className="bg-tb-bg p-3 overflow-hidden">
          <IndicatorsPanel detectors={state.detectors} />
        </div>

        {/* Center — Heatmap */}
        <div className="bg-tb-bg p-3 overflow-hidden">
          <StrikeHeatmap strikeMap={state.strike_map} atm={state.atm} />
        </div>

        {/* Right — Brain (spans 2 rows) */}
        <div className="bg-tb-bg p-4 overflow-y-auto row-span-2">
          <BrainDashboard confluence={state.confluence} brain={state.brain} spot={state.spot} />
        </div>

        {/* Bottom — Alert Log (spans 2 cols) */}
        <div className="bg-tb-bg p-3 overflow-hidden col-span-2">
          <AlertLog alerts={state.alert_log} />
        </div>
      </div>
    </div>
  )
}
