import { useState } from 'react'

export default function KiteLoginPage({ step, loginUrl, userName, error, loading, onSetCredentials, onCallback, onLogout }: {
  step: 'kite_credentials' | 'kite_login'
  loginUrl: string
  userName: string
  error: string
  loading: boolean
  onSetCredentials: (apiKey: string, apiSecret: string) => void
  onCallback: (requestToken: string) => void
  onLogout: () => void
}) {
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [requestToken, setRequestToken] = useState('')

  return (
    <div className="min-h-screen bg-tb-bg flex items-center justify-center p-4">
      <div className="w-full max-w-lg animate-slide-up">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-gradient-to-br from-neon-cyan to-neon-blue rounded-lg flex items-center justify-center text-sm font-black text-tb-bg">TB</div>
            <span className="text-xl font-extrabold tracking-tight text-tb-text">TRADE BRO</span>
          </div>
          <p className="text-neon-green text-sm font-medium">Welcome, {userName}</p>
        </div>

        <div className="bg-tb-card border border-tb-border rounded-2xl p-8">
          {step === 'kite_credentials' ? (
            <>
              <h2 className="text-lg font-bold text-tb-text mb-1">Connect Zerodha Kite</h2>
              <p className="text-tb-muted text-xs mb-6">Enter your Kite Connect API credentials to access live market data</p>

              <form onSubmit={(e) => { e.preventDefault(); if (apiKey && apiSecret) onSetCredentials(apiKey, apiSecret) }}>
                <div className="space-y-4">
                  <div>
                    <label className="text-[11px] text-tb-muted uppercase tracking-wider mb-1.5 block">API Key</label>
                    <input
                      type="text"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Your Kite API Key"
                      className="w-full bg-tb-bg border border-tb-border rounded-xl px-4 py-3 text-sm font-mono text-tb-text placeholder:text-tb-muted/40 focus:border-neon-cyan/50 transition-all"
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-tb-muted uppercase tracking-wider mb-1.5 block">API Secret</label>
                    <input
                      type="password"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                      placeholder="Your Kite API Secret"
                      className="w-full bg-tb-bg border border-tb-border rounded-xl px-4 py-3 text-sm font-mono text-tb-text placeholder:text-tb-muted/40 focus:border-neon-cyan/50 transition-all"
                    />
                  </div>
                </div>

                {error && (
                  <div className="mt-3 text-neon-red text-xs bg-red-950/20 border border-red-900/30 rounded-lg px-3 py-2">{error}</div>
                )}

                <button type="submit" disabled={!apiKey || !apiSecret || loading}
                  className="w-full mt-6 bg-gradient-to-r from-neon-green to-emerald-500 text-tb-bg font-bold text-sm py-3.5 rounded-xl hover:opacity-90 disabled:opacity-40 transition-all">
                  {loading ? 'Connecting...' : 'Login to Zerodha'}
                </button>
              </form>
            </>
          ) : (
            <>
              <h2 className="text-lg font-bold text-tb-text mb-1">Complete Zerodha Login</h2>
              <p className="text-tb-muted text-xs mb-4">Step 1: Click below to login to Zerodha. Step 2: After login, paste the request token from the redirect URL.</p>

              <a href={loginUrl} target="_blank" rel="noopener noreferrer"
                className="block w-full text-center bg-gradient-to-r from-orange-500 to-red-500 text-white font-bold text-sm py-3.5 rounded-xl hover:opacity-90 transition-all mb-6">
                Open Zerodha Login
              </a>

              <div className="border-t border-tb-border pt-5">
                <label className="text-[11px] text-tb-muted uppercase tracking-wider mb-1.5 block">Request Token</label>
                <p className="text-[10px] text-tb-muted/60 mb-2">After Zerodha login, you'll be redirected. Copy the <code className="text-neon-cyan">request_token</code> from the URL.</p>
                <input
                  type="text"
                  value={requestToken}
                  onChange={(e) => setRequestToken(e.target.value)}
                  placeholder="Paste request_token here"
                  className="w-full bg-tb-bg border border-tb-border rounded-xl px-4 py-3 text-sm font-mono text-tb-text placeholder:text-tb-muted/40 focus:border-neon-cyan/50 transition-all"
                />

                {error && (
                  <div className="mt-3 text-neon-red text-xs bg-red-950/20 border border-red-900/30 rounded-lg px-3 py-2">{error}</div>
                )}

                <button onClick={() => { if (requestToken) onCallback(requestToken) }}
                  disabled={!requestToken || loading}
                  className="w-full mt-4 bg-gradient-to-r from-neon-cyan to-neon-blue text-tb-bg font-bold text-sm py-3.5 rounded-xl hover:opacity-90 disabled:opacity-40 transition-all">
                  {loading ? 'Authenticating...' : 'Complete Login'}
                </button>
              </div>
            </>
          )}

          <button onClick={onLogout} className="w-full mt-4 text-tb-muted text-xs hover:text-neon-red transition-colors py-2">
            Use a different license key
          </button>
        </div>
      </div>
    </div>
  )
}
