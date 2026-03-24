import { useState, useCallback, useEffect } from 'react'

const API = import.meta.env.VITE_API_URL || ''

export type AuthStep = 'license' | 'kite_credentials' | 'kite_redirect' | 'authenticated'

export interface Session {
  session_id: string
  user_name: string
  is_authenticated: boolean
  has_api_key: boolean
}

function loadStep(): AuthStep {
  const s = localStorage.getItem('tb_step') as AuthStep | null
  if (s && ['kite_credentials', 'kite_redirect', 'authenticated'].includes(s)) return s
  return 'license'
}

function loadSession(): Session | null {
  try { const s = localStorage.getItem('tb_session'); return s ? JSON.parse(s) : null } catch { return null }
}

export function useSession() {
  const [step, setStepState] = useState<AuthStep>(loadStep)
  const [session, setSessionState] = useState<Session | null>(loadSession)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const setStep = (s: AuthStep) => { setStepState(s); localStorage.setItem('tb_step', s) }
  const setSession = (sess: Session | null) => {
    setSessionState(sess)
    if (sess) { localStorage.setItem('tb_session', JSON.stringify(sess)); localStorage.setItem('tb_session_id', sess.session_id) }
    else { localStorage.removeItem('tb_session'); localStorage.removeItem('tb_session_id') }
  }

  // Auto-detect request_token from URL after Zerodha redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('request_token')
    const status = params.get('status')
    if (token && status === 'success') {
      // Clean URL immediately
      window.history.replaceState({}, '', window.location.pathname)
      // Go directly to authenticated — no spinner, no blank screen
      setStep('authenticated')
      setLoading(false)
      const sess = loadSession()
      if (sess) {
        fetch(`${API}/api/kite/callback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sess.session_id, request_token: token }),
        })
          .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
          .then(data => {
            if (data.authenticated) {
              const updated = { ...sess, is_authenticated: true, user_name: data.user_name || sess.user_name }
              setSession(updated)
              setStep('authenticated')
            } else {
              setError(data.detail || 'Zerodha auth failed. Try again.')
              setStep('kite_credentials')
            }
          })
          .catch((e) => { setError(`Server error: ${e.message}. Try again.`); setStep('kite_credentials') })
          .finally(() => setLoading(false))
      } else {
        // No session found — start over
        setStep('license')
        setLoading(false)
      }
    }
  }, [])

  const verifyLicense = useCallback(async (key: string) => {
    setLoading(true); setError('')
    try {
      const r = await fetch(`${API}/api/license/verify`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: key }),
      })
      const data = await r.json()
      if (!data.valid) { setError(data.error || 'Invalid license key'); return }
      const sess = data.session as Session
      setSession(sess)
      sess.is_authenticated ? setStep('authenticated') : setStep('kite_credentials')
    } catch { setError('Server offline. Check connection.') }
    finally { setLoading(false) }
  }, [])

  const setKiteCredentials = useCallback(async (apiKey: string, apiSecret: string) => {
    if (!session) return
    setLoading(true); setError('')
    try {
      const r = await fetch(`${API}/api/kite/credentials`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id, api_key: apiKey, api_secret: apiSecret }),
      })
      const data = await r.json()
      if (data.login_url) {
        // Redirect directly to Zerodha — no intermediate step
        window.location.href = data.login_url
      } else {
        setError('Failed to set credentials')
      }
    } catch { setError('Server offline') }
    finally { setLoading(false) }
  }, [session])

  const logout = useCallback(async () => {
    if (session) fetch(`${API}/api/logout/${session.session_id}`, { method: 'POST' }).catch(() => {})
    localStorage.removeItem('tb_session'); localStorage.removeItem('tb_session_id')
    localStorage.removeItem('tb_step')
    setSession(null); setStepState('license'); setError('')
  }, [session])

  return { step, session, error, loading, verifyLicense, setKiteCredentials, logout }
}
