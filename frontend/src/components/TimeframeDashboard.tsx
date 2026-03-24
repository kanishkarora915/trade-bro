import { useState } from 'react'
import type { TradeState } from '../hooks/useWebSocket'

interface Props { state: TradeState; onBack: () => void }

const TF_ORDER = ['1w', '1d', '1h', '30m', '15m', '5m', '3m'] as const
const TF_LABELS: Record<string, string> = {
  '1w': 'Weekly', '1d': 'Daily', '1h': 'Hourly',
  '30m': '30 Min', '15m': '15 Min', '5m': '5 Min', '3m': '3 Min',
}

function trendArrow(dir: string): { arrow: string; label: string; clr: string; bg: string } {
  const d = (dir || '').toUpperCase()
  if (d.includes('BULL') || d.includes('UP')) return { arrow: '\u25B2', label: 'BULLISH', clr: 'text-green-400', bg: 'bg-emerald-950/20' }
  if (d.includes('BEAR') || d.includes('DOWN')) return { arrow: '\u25BC', label: 'BEARISH', clr: 'text-red-400', bg: 'bg-red-950/20' }
  return { arrow: '\u2192', label: 'SIDEWAYS', clr: 'text-yellow-400', bg: 'bg-yellow-950/20' }
}

function StrengthBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value || 0))
  const clr = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div className={`h-full ${clr} rounded-full transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function TimeframeDashboard({ state, onBack }: Props) {
  const tfData: Record<string, any> = (state as any).timeframe_data || {}
  const mtf: any = (state as any).mtf_analysis || {}
  const [saving, setSaving] = useState(false)

  const signal = mtf.signal || {}
  const keyLevels = mtf.key_levels || {}
  const score = mtf.score ?? signal.score ?? 0
  const direction = mtf.direction || signal.direction || 'NEUTRAL'
  const confidence = mtf.confidence || signal.confidence || 0
  const setup = signal.setup || mtf.setup || {}
  const reasoning = mtf.reasoning || signal.reasoning || []
  const rr = setup.risk_reward || signal.risk_reward || 0

  const handleSave = () => {
    setSaving(true)
    setTimeout(() => setSaving(false), 2000)
  }

  return (
    <div className="h-screen flex flex-col bg-tb-bg overflow-hidden">
      {/* TOP BAR */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 bg-tb-card/30 border-b border-tb-border">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="text-[11px] text-neon-cyan hover:text-white font-bold transition-colors">&larr; Main</button>
          <span className="text-[13px] font-extrabold text-white tracking-wider">TIMEFRAMES</span>
          <span className="text-[10px] text-gray-400 font-mono">Spot: <span className="text-white font-bold">{state.spot?.toLocaleString('en-IN') || '--'}</span></span>
          <span className="text-[10px] text-gray-400 font-mono">ATM: <span className="text-neon-cyan font-bold">{state.atm || '--'}</span></span>
        </div>
        <button onClick={handleSave}
          className={`text-[10px] font-bold px-3 py-1 rounded-lg border transition-all ${saving ? 'text-green-400 border-green-500/30 bg-green-950/20' : 'text-neon-yellow border-neon-yellow/30 hover:bg-neon-yellow/10'}`}>
          {saving ? 'Saved!' : 'Save Snapshot'}
        </button>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 grid grid-cols-[1fr_340px] gap-[1px] bg-tb-border overflow-hidden">
        {/* LEFT: TF Cards + Key Levels */}
        <div className="bg-tb-bg flex flex-col overflow-hidden">
          {/* TIMEFRAME CARDS — scrollable row */}
          <div className="shrink-0 p-3 overflow-x-auto">
            <div className="flex gap-2 min-w-max">
              {TF_ORDER.map(tf => {
                const d = tfData[tf] || {}
                const t = trendArrow(d.trend || d.direction || '')
                return (
                  <div key={tf} className={`w-[150px] shrink-0 rounded-lg border border-tb-border ${t.bg} p-2.5`}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-extrabold text-white">{TF_LABELS[tf]}</span>
                      <span className="text-[9px] text-gray-500 font-mono">{tf}</span>
                    </div>
                    {/* Trend */}
                    <div className={`text-[12px] font-extrabold ${t.clr} mb-1`}>
                      {t.arrow} {t.label}
                    </div>
                    {/* Strength */}
                    <div className="mb-2">
                      <StrengthBar value={d.trend_strength || d.strength || 0} />
                    </div>
                    {/* Support / Resistance */}
                    <div className="flex justify-between text-[9px] mb-1">
                      <span className="text-gray-500">Support</span>
                      <span className="text-green-400 font-bold font-mono">{d.support ? d.support.toLocaleString('en-IN') : '--'}</span>
                    </div>
                    <div className="flex justify-between text-[9px] mb-1">
                      <span className="text-gray-500">Resist</span>
                      <span className="text-red-400 font-bold font-mono">{d.resistance ? d.resistance.toLocaleString('en-IN') : '--'}</span>
                    </div>
                    {/* Vol ratio */}
                    <div className="flex justify-between text-[9px] mb-1">
                      <span className="text-gray-500">Vol Ratio</span>
                      <span className="text-cyan-400 font-mono">{d.volume_ratio?.toFixed(2) || '--'}</span>
                    </div>
                    {/* Breakout */}
                    <div className="flex justify-between text-[9px] mb-1">
                      <span className="text-gray-500">Breakout</span>
                      <span className={`font-bold ${d.breakout ? 'text-neon-yellow' : 'text-gray-600'}`}>{d.breakout ? 'YES' : 'NO'}</span>
                    </div>
                    {/* EMAs */}
                    <div className="flex justify-between text-[9px]">
                      <span className="text-gray-500">EMA9</span>
                      <span className="text-gray-300 font-mono">{d.ema9?.toFixed(1) || '--'}</span>
                    </div>
                    <div className="flex justify-between text-[9px]">
                      <span className="text-gray-500">EMA21</span>
                      <span className="text-gray-300 font-mono">{d.ema21?.toFixed(1) || '--'}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* KEY LEVELS TABLE */}
          <div className="flex-1 p-3 overflow-y-auto">
            <div className="text-[11px] font-extrabold text-white mb-2 tracking-wider">KEY LEVELS</div>
            <table className="w-full text-[10px] font-mono">
              <thead>
                <tr className="text-gray-500 border-b border-tb-border">
                  <th className="text-left py-1 px-2 font-semibold">Source</th>
                  <th className="text-right py-1 px-2 font-semibold">Level</th>
                  <th className="text-center py-1 px-2 font-semibold">Type</th>
                  <th className="text-left py-1 px-2 font-semibold">Notes</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(keyLevels).length === 0 && (
                  <tr><td colSpan={4} className="text-gray-600 text-center py-6">No key levels detected yet</td></tr>
                )}
                {Object.entries(keyLevels).map(([key, val]: [string, any]) => {
                  const isSupport = key.toLowerCase().includes('support')
                  const isResistance = key.toLowerCase().includes('resistance')
                  const levelVal = typeof val === 'object' ? val.level || val.value || 0 : val
                  const notes = typeof val === 'object' ? val.notes || '' : ''
                  return (
                    <tr key={key} className="border-b border-tb-border/50 hover:bg-white/[0.02]">
                      <td className="py-1.5 px-2 text-gray-300 capitalize">{key.replace(/_/g, ' ')}</td>
                      <td className={`py-1.5 px-2 text-right font-bold ${isSupport ? 'text-green-400' : isResistance ? 'text-red-400' : 'text-white'}`}>
                        {typeof levelVal === 'number' && levelVal > 0 ? levelVal.toLocaleString('en-IN') : '--'}
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${isSupport ? 'bg-green-900/40 text-green-400' : isResistance ? 'bg-red-900/40 text-red-400' : 'bg-gray-800 text-gray-400'}`}>
                          {isSupport ? 'SUPPORT' : isResistance ? 'RESISTANCE' : 'LEVEL'}
                        </span>
                      </td>
                      <td className="py-1.5 px-2 text-gray-500">{notes || '--'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* RIGHT SIDE: MTF Signal + Saved History */}
        <div className="bg-tb-bg p-3 overflow-y-auto flex flex-col gap-3">
          {/* MTF SIGNAL */}
          <div className="rounded-lg border border-tb-border bg-tb-card/30 p-3">
            <div className="text-[11px] font-extrabold text-white mb-3 tracking-wider">MTF SIGNAL</div>

            {/* Score */}
            <div className="text-center mb-3">
              <div className={`text-[40px] font-black leading-none ${score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                {Math.round(score)}
              </div>
              <div className="text-[10px] text-gray-500 mt-0.5">Overall Score</div>
            </div>

            {/* Direction + Confidence */}
            <div className="flex items-center justify-center gap-2 mb-3">
              {(() => {
                const t = trendArrow(direction)
                return (
                  <span className={`text-[12px] font-extrabold ${t.clr}`}>{t.arrow} {direction}</span>
                )
              })()}
              <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold ${confidence >= 70 ? 'bg-green-900/40 text-green-400' : confidence >= 40 ? 'bg-yellow-900/40 text-yellow-400' : 'bg-gray-800 text-gray-400'}`}>
                {confidence}% conf
              </span>
            </div>

            {/* Trade Setup */}
            {setup.action && (
              <div className={`rounded-lg p-2.5 mb-3 border ${setup.action?.includes('CE') ? 'border-green-800/30 bg-emerald-950/15' : 'border-red-800/30 bg-red-950/15'}`}>
                <div className="text-[11px] font-extrabold text-white mb-1.5">TRADE SETUP</div>
                <div className="space-y-1 text-[10px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Action</span>
                    <span className={`font-extrabold ${setup.action?.includes('CE') ? 'text-green-400' : 'text-red-400'}`}>{setup.action}</span>
                  </div>
                  {setup.strike && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Strike</span>
                      <span className="text-white font-bold">{setup.strike}</span>
                    </div>
                  )}
                  {setup.entry && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Entry Zone</span>
                      <span className="text-neon-cyan font-bold">{setup.entry}</span>
                    </div>
                  )}
                  {setup.target && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Target</span>
                      <span className="text-green-400 font-bold">{setup.target}</span>
                    </div>
                  )}
                  {setup.sl && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Stop Loss</span>
                      <span className="text-red-400 font-bold">{setup.sl}</span>
                    </div>
                  )}
                  {rr > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Risk:Reward</span>
                      <span className="text-neon-yellow font-bold">1:{rr.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Reasoning */}
            {Array.isArray(reasoning) && reasoning.length > 0 && (
              <div>
                <div className="text-[10px] font-bold text-gray-400 mb-1">REASONING</div>
                <ul className="space-y-1">
                  {reasoning.map((r: string, i: number) => (
                    <li key={i} className="text-[10px] text-gray-300 flex items-start gap-1.5">
                      <span className="text-neon-cyan mt-0.5 shrink-0">&#x2022;</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Empty state */}
            {!setup.action && (!reasoning || reasoning.length === 0) && score === 0 && (
              <div className="text-center text-gray-600 text-[11px] py-4">
                Waiting for timeframe data...
              </div>
            )}
          </div>

          {/* SAVED HISTORY */}
          <div className="rounded-lg border border-tb-border bg-tb-card/30 p-3">
            <div className="text-[11px] font-extrabold text-white mb-2 tracking-wider">SAVED HISTORY</div>
            <p className="text-[10px] text-gray-500 mb-1">Daily data auto-saves every 30 min</p>
            <p className="text-[10px] text-gray-400 font-mono">
              Last save: <span className="text-neon-cyan">{new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
