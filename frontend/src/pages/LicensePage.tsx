import { useState } from 'react'

export default function LicensePage({ onVerify, error, loading }: {
  onVerify: (key: string) => void; error: string; loading: boolean
}) {
  const [key, setKey] = useState('')

  return (
    <div className="min-h-screen bg-tb-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-neon-cyan to-neon-blue rounded-lg flex items-center justify-center text-xl font-black text-tb-bg">TB</div>
            <span className="text-2xl font-extrabold tracking-tight text-tb-text">TRADE BRO</span>
          </div>
          <p className="text-tb-muted text-sm">Options Boom Detector — Nifty 50</p>
          <p className="text-tb-muted/50 text-xs mt-1">by Kanishk Arora</p>
        </div>

        {/* Card */}
        <div className="bg-tb-card border border-tb-border rounded-2xl p-8">
          <h2 className="text-lg font-bold text-tb-text mb-1">Enter License Key</h2>
          <p className="text-tb-muted text-xs mb-6">Enter your license key to unlock the dashboard</p>

          <form onSubmit={(e) => { e.preventDefault(); if (key.trim()) onVerify(key) }}>
            <input
              type="text"
              value={key}
              onChange={(e) => setKey(e.target.value.toUpperCase())}
              placeholder="TRADE-BRO-001"
              className="w-full bg-tb-bg border border-tb-border rounded-xl px-4 py-3.5 text-sm font-mono text-tb-text placeholder:text-tb-muted/40 focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/20 transition-all"
              autoFocus
              disabled={loading}
            />

            {error && (
              <div className="mt-3 text-neon-red text-xs bg-red-950/20 border border-red-900/30 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!key.trim() || loading}
              className="w-full mt-5 bg-gradient-to-r from-neon-cyan to-neon-blue text-tb-bg font-bold text-sm py-3.5 rounded-xl hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-tb-bg/30 border-t-tb-bg rounded-full animate-spin" />
                  Verifying...
                </span>
              ) : 'Unlock Dashboard'}
            </button>
          </form>
        </div>

        <p className="text-center text-tb-muted/30 text-[10px] mt-6">
          TRADE BRO v1.0 — Institutional Options Intelligence
        </p>
      </div>
    </div>
  )
}
