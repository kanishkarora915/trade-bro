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
  const { step, session, error, loading, verifyLicense, setKiteCredentials, logout } = useSession()
  const sessionId = step === 'authenticated' && session ? session.session_id : null
  const { state, connected, latency } = useWebSocket(sessionId)
  useAlerts(state.confluence)

  // Loading screen (auto-detecting token from URL)
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

  if (step === 'license') {
    return <LicensePage onVerify={verifyLicense} error={error} loading={loading} />
  }

  if (step === 'kite_credentials') {
    return (
      <KiteLoginPage
        userName={session?.user_name || ''}
        error={error}
        loading={loading}
        onSetCredentials={setKiteCredentials}
        onLogout={logout}
      />
    )
  }

  const flash = state.confluence.score >= 86 ? 'flash-red' : state.confluence.score >= 76 ? 'flash-green' : ''

  return (
    <div className={`h-screen flex flex-col bg-tb-bg overflow-hidden ${flash}`}>
      <TopBar spot={state.spot} atm={state.atm} connected={connected} latency={latency} userName={session?.user_name || ''} onLogout={logout} />

      {state.error && (
        <div className="shrink-0 bg-red-950/30 border-b border-red-900/30 px-4 py-1.5 text-[11px] text-neon-red font-mono">
          API Error: {state.error}
        </div>
      )}

      <div className="flex-1 grid grid-cols-[280px_1fr_380px] grid-rows-[1fr_150px] gap-[1px] bg-tb-border overflow-hidden">
        <div className="bg-tb-bg p-3 overflow-hidden"><IndicatorsPanel detectors={state.detectors} /></div>
        <div className="bg-tb-bg p-3 overflow-hidden"><StrikeHeatmap strikeMap={state.strike_map} atm={state.atm} /></div>
        <div className="bg-tb-bg p-4 overflow-y-auto row-span-2"><BrainDashboard confluence={state.confluence} brain={state.brain} spot={state.spot} /></div>
        <div className="bg-tb-bg p-3 overflow-hidden col-span-2"><AlertLog alerts={state.alert_log} /></div>
      </div>
    </div>
  )
}
