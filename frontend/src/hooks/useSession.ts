import { useState, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL || ''

export type AuthStep = 'license' | 'kite_credentials' | 'kite_login' | 'authenticated'

export interface Session {
  session_id: string
  user_name: string
  is_authenticated: boolean
  has_api_key: boolean
}

function loadStep(): AuthStep {
  const saved = localStorage.getItem('tb_step') as AuthStep | null
  if (saved && ['kite_credentials', 'kite_login', 'authenticated'].includes(saved)) {
    return saved
  }
  return 'license'
}

function loadSession(): Session | null {
  const s = localStorage.getItem('tb_session')
  if (s) {
    try { return JSON.parse(s) } catch { return null }
  }
  return null
}

export function useSession() {
  const [step, setStepState] = useState<AuthStep>(loadStep)
  const [session, setSessionState] = useState<Session | null>(loadSession)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loginUrl, setLoginUrl] = useState(() => localStorage.getItem('tb_login_url') || '')

  const setStep = (s: AuthStep) => {
    setStepState(s)
    localStorage.setItem('tb_step', s)
  }

  const setSession = (sess: Session | null) => {
    setSessionState(sess)
    if (sess) {
      localStorage.setItem('tb_session', JSON.stringify(sess))
      localStorage.setItem('tb_session_id', sess.session_id)
    } else {
      localStorage.removeItem('tb_session')
      localStorage.removeItem('tb_session_id')
    }
  }

  const verifyLicense = useCallback(async (key: string) => {
    setLoading(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/license/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: key }),
      })
      const data = await r.json()
      if (!data.valid) {
        setError(data.error || 'Invalid license key')
        return
      }
      const sess = data.session as Session
      setSession(sess)
      if (sess.is_authenticated) {
        setStep('authenticated')
      } else {
        setStep('kite_credentials')
      }
    } catch {
      setError('Server offline. Check connection.')
    } finally {
      setLoading(false)
    }
  }, [])

  const setKiteCredentials = useCallback(async (apiKey: string, apiSecret: string) => {
    if (!session) return
    setLoading(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/kite/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id, api_key: apiKey, api_secret: apiSecret }),
      })
      const data = await r.json()
      if (data.login_url) {
        setLoginUrl(data.login_url)
        localStorage.setItem('tb_login_url', data.login_url)
        setStep('kite_login')
      } else {
        setError('Failed to set credentials')
      }
    } catch {
      setError('Server offline')
    } finally {
      setLoading(false)
    }
  }, [session])

  const handleCallback = useCallback(async (requestToken: string) => {
    if (!session) return
    setLoading(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/kite/callback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id, request_token: requestToken }),
      })
      const data = await r.json()
      if (data.authenticated) {
        const updated = { ...session, is_authenticated: true }
        setSession(updated)
        setStep('authenticated')
      } else {
        setError(data.detail || 'Auth failed')
      }
    } catch (e: any) {
      setError(e.message || 'Callback failed')
    } finally {
      setLoading(false)
    }
  }, [session])

  const logout = useCallback(async () => {
    if (session) {
      fetch(`${API}/api/logout/${session.session_id}`, { method: 'POST' }).catch(() => {})
    }
    localStorage.removeItem('tb_session')
    localStorage.removeItem('tb_session_id')
    localStorage.removeItem('tb_step')
    localStorage.removeItem('tb_login_url')
    setSession(null)
    setStepState('license')
    setError('')
    setLoginUrl('')
  }, [session])

  return { step, session, error, loading, loginUrl, verifyLicense, setKiteCredentials, handleCallback, logout }
}
