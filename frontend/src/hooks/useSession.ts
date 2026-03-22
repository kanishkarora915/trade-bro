import { useState, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL || ''

export type AuthStep = 'license' | 'kite_credentials' | 'kite_login' | 'authenticated'

export interface Session {
  session_id: string
  user_name: string
  is_authenticated: boolean
  has_api_key: boolean
}

export function useSession() {
  const [step, setStep] = useState<AuthStep>(() => {
    const saved = sessionStorage.getItem('tb_session_id')
    const savedStep = sessionStorage.getItem('tb_step') as AuthStep
    return saved && savedStep === 'authenticated' ? 'authenticated' : 'license'
  })
  const [session, setSession] = useState<Session | null>(() => {
    const s = sessionStorage.getItem('tb_session')
    return s ? JSON.parse(s) : null
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loginUrl, setLoginUrl] = useState('')

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
      sessionStorage.setItem('tb_session_id', sess.session_id)
      sessionStorage.setItem('tb_session', JSON.stringify(sess))
      if (sess.is_authenticated) {
        setStep('authenticated')
        sessionStorage.setItem('tb_step', 'authenticated')
      } else {
        setStep('kite_credentials')
      }
    } catch (e: any) {
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
        sessionStorage.setItem('tb_session', JSON.stringify(updated))
        sessionStorage.setItem('tb_step', 'authenticated')
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
    sessionStorage.clear()
    setSession(null)
    setStep('license')
    setError('')
    setLoginUrl('')
  }, [session])

  return { step, session, error, loading, loginUrl, verifyLicense, setKiteCredentials, handleCallback, logout }
}
