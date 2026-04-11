/**
 * VPIN Dashboard — "Buyer's Brain"
 * Monitors flow toxicity to find BUY opportunities.
 * Not strict gatekeeper — informational layer for the buyer.
 *
 * Futures VPIN = leading indicator
 * CE vs PE side = which side is active
 * Conclusion: where to buy based on seller flow
 */

import { useState } from 'react'

function VPINGauge({ value, size = 100 }: { value: number; size?: number }) {
  const pct = Math.min(1, Math.max(0, value))
  const angle = -90 + pct * 180
  const r = size / 2 - 8
  const cx = size / 2
  const cy = size / 2

  const arcPath = (startDeg: number, endDeg: number, radius: number) => {
    const s = (startDeg * Math.PI) / 180
    const e = (endDeg * Math.PI) / 180
    return `M ${cx + radius * Math.cos(s)} ${cy + radius * Math.sin(s)} A ${radius} ${radius} 0 ${endDeg - startDeg > 180 ? 1 : 0} 1 ${cx + radius * Math.cos(e)} ${cy + radius * Math.sin(e)}`
  }

  const color = pct >= 0.85 ? '#EF4444' : pct >= 0.70 ? '#F97316' : pct >= 0.55 ? '#EAB308' : '#10B981'
  const needleAngle = (angle * Math.PI) / 180

  return (
    <svg width={size} height={size / 2 + 12} viewBox={`0 0 ${size} ${size / 2 + 12}`}>
      <path d={arcPath(-180, 0, r)} fill="none" stroke="#1a1a2e" strokeWidth={6} />
      <path d={arcPath(-180, angle - 90, r)} fill="none" stroke={color} strokeWidth={6} strokeLinecap="round" />
      <line x1={cx} y1={cy} x2={cx + (r - 12) * Math.cos(needleAngle)} y2={cy + (r - 12) * Math.sin(needleAngle)} stroke="white" strokeWidth={2} />
      <circle cx={cx} cy={cy} r={2.5} fill="white" />
      <text x={cx} y={cy + 12} textAnchor="middle" fill={color} fontSize="14" fontWeight="900" fontFamily="JetBrains Mono, monospace">
        {(pct * 100).toFixed(1)}%
      </text>
    </svg>
  )
}

function Sparkline({ data, w = 160, h = 32 }: { data: number[]; w?: number; h?: number }) {
  if (!data.length) return <span className="text-[9px] text-gray-700">No data</span>
  const max = Math.max(...data, 0.01)
  const min = Math.min(...data, 0)
  const range = max - min || 0.01
  const pts = data.map((v, i) => `${(i / Math.max(data.length - 1, 1)) * w},${h - ((v - min) / range) * (h - 4) - 2}`).join(' ')
  const lastColor = data[data.length - 1] >= 0.7 ? '#F97316' : data[data.length - 1] >= 0.55 ? '#EAB308' : '#10B981'
  return (
    <svg width={w} height={h}>
      <polyline points={pts} fill="none" stroke="#0A84FF" strokeWidth={1.5} />
      <circle cx={w} cy={h - ((data[data.length - 1] - min) / range) * (h - 4) - 2} r={3} fill={lastColor} />
    </svg>
  )
}

function InstrumentCard({ inst }: { inst: any }) {
  const v = inst.vpin || 0
  const color = v >= 0.85 ? 'border-red-500/40 bg-red-950/15' : v >= 0.70 ? 'border-orange-500/40 bg-orange-950/15' : v >= 0.55 ? 'border-yellow-500/40 bg-yellow-950/15' : 'border-emerald-500/30 bg-emerald-950/10'
  const label = v >= 0.85 ? 'EXTREME' : v >= 0.70 ? 'HIGH' : v >= 0.55 ? 'ELEVATED' : 'NORMAL'
  const labelClr = v >= 0.85 ? 'text-red-400' : v >= 0.70 ? 'text-orange-400' : v >= 0.55 ? 'text-yellow-400' : 'text-emerald-400'

  const buyPct = (inst.buy_volume || 0) + (inst.sell_volume || 0) > 0
    ? ((inst.buy_volume || 0) / ((inst.buy_volume || 0) + (inst.sell_volume || 0))) * 100 : 50

  return (
    <div className={`border rounded-xl p-3 ${color}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-bold text-white">{inst.name}</span>
        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${labelClr} bg-black/30`}>{label}</span>
      </div>
      <div className="flex justify-center"><VPINGauge value={v} size={90} /></div>
      {/* Buy/Sell bar */}
      <div className="mt-2">
        <div className="flex justify-between text-[9px] font-mono mb-0.5">
          <span className="text-emerald-400">{buyPct.toFixed(0)}% Buy</span>
          <span className="text-red-400">{(100 - buyPct).toFixed(0)}% Sell</span>
        </div>
        <div className="h-1.5 bg-gray-800 rounded-full flex overflow-hidden">
          <div className="bg-emerald-500" style={{ width: `${buyPct}%` }} />
          <div className="bg-red-500 flex-1" />
        </div>
      </div>
      <div className="mt-2"><Sparkline data={inst.sparkline || []} /></div>
      <div className="flex justify-between mt-1.5 text-[9px] text-gray-600 font-mono">
        <span>{inst.buckets_completed} buckets</span>
        <span>{(inst.total_ticks || 0).toLocaleString('en-IN')} ticks</span>
      </div>
    </div>
  )
}

export default function VPINDashboard({ state }: { state: any }) {
  const vpin = (state as any).vpin || { instruments: {}, market_vpin: 0, market_signal: 'NEUTRAL' }
  const instruments = vpin.instruments || {}
  const entries = Object.entries(instruments) as [string, any][]

  // Buyer's interpretation
  const futVpin = entries.find(([_, i]) => i.name?.includes('FUT'))?.[1]?.vpin || 0
  const ceVpin = vpin.ce_vpin || 0
  const peVpin = vpin.pe_vpin || 0

  let buyerAdvice = ''
  let adviceColor = 'text-gray-400'

  if (futVpin >= 0.70) {
    buyerAdvice = 'HEAVY informed flow on futures — big move coming. Wait for direction clarity, then BUY aggressively.'
    adviceColor = 'text-orange-400'
  } else if (futVpin >= 0.55) {
    buyerAdvice = 'Informed activity building on futures. Watch CE vs PE side — whichever side is more active, BUY the opposite.'
    adviceColor = 'text-yellow-400'
  } else if (ceVpin > peVpin + 0.1) {
    buyerAdvice = 'CE side more toxic than PE — call sellers under pressure. Consider BUY CE.'
    adviceColor = 'text-emerald-400'
  } else if (peVpin > ceVpin + 0.1) {
    buyerAdvice = 'PE side more toxic than CE — put sellers under pressure. Consider BUY PE.'
    adviceColor = 'text-red-400'
  } else {
    buyerAdvice = 'Normal flow. No informed activity detected. Use other tabs (Bob, Sellers) for signals.'
    adviceColor = 'text-gray-500'
  }

  return (
    <div className="h-full flex flex-col bg-[#080808] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-[#0a0f14] border-b border-blue-900/30 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center text-[10px] font-black text-black">VP</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.15em] text-[#0A84FF]">BUYER'S BRAIN — VPIN</h1>
              <p className="text-[9px] text-blue-800">Flow toxicity = informed traders active. Track them, ride their move.</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-[8px] text-gray-600">MARKET FLOW</p>
            <p className={`text-xl font-black font-mono ${futVpin >= 0.70 ? 'text-orange-400' : futVpin >= 0.55 ? 'text-yellow-400' : 'text-emerald-400'}`}>
              {(futVpin * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Buyer's Advice — the conclusion */}
        <div className={`border rounded-xl p-4 ${
          futVpin >= 0.70 ? 'border-orange-500/30 bg-orange-950/15' :
          futVpin >= 0.55 ? 'border-yellow-500/30 bg-yellow-950/15' :
          'border-gray-800 bg-gray-900/30'
        }`}>
          <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-1">Buyer's Conclusion</p>
          <p className={`text-[12px] font-bold leading-relaxed ${adviceColor}`}>{buyerAdvice}</p>
        </div>

        {/* CE vs PE Flow */}
        {(ceVpin > 0 || peVpin > 0) && (
          <div className="border border-gray-800 rounded-xl p-4">
            <p className="text-[9px] text-blue-400 uppercase tracking-widest font-bold mb-3">CE vs PE Toxicity</p>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-emerald-400 font-bold">CE SIDE</span>
                  <span className="text-sm font-black font-mono text-emerald-400">{(ceVpin * 100).toFixed(1)}%</span>
                </div>
                <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 transition-all" style={{ width: `${Math.min(100, ceVpin * 100)}%` }} />
                </div>
              </div>
              <span className="text-gray-700 text-xs">vs</span>
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-red-400 font-bold">PE SIDE</span>
                  <span className="text-sm font-black font-mono text-red-400">{(peVpin * 100).toFixed(1)}%</span>
                </div>
                <div className="h-3 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 transition-all" style={{ width: `${Math.min(100, peVpin * 100)}%` }} />
                </div>
              </div>
            </div>
            <p className="text-[10px] text-gray-500 mt-2 text-center font-mono">{vpin.flow_bias || ''}</p>
            <p className="text-[9px] text-gray-700 mt-1 text-center">
              {ceVpin > peVpin + 0.1 ? 'CE sellers under stress → BUY CE opportunity' :
               peVpin > ceVpin + 0.1 ? 'PE sellers under stress → BUY PE opportunity' :
               'Balanced — no clear edge from VPIN alone'}
            </p>
          </div>
        )}

        {/* Instrument Cards */}
        {entries.length > 0 ? (
          <div className="grid grid-cols-3 gap-3">
            {entries.map(([token, inst]) => <InstrumentCard key={token} inst={inst} />)}
          </div>
        ) : (
          <div className="border border-gray-800 rounded-xl p-6 text-center">
            <p className="text-gray-500">Waiting for ticks...</p>
            <p className="text-[10px] text-gray-700 mt-1">VPIN activates when market opens and Kite ticker sends live data.</p>
          </div>
        )}

        {/* How to use — short and actionable */}
        <div className="border border-gray-800 rounded-xl p-3 text-[10px] text-gray-600">
          <p className="text-blue-400 font-bold text-[9px] uppercase tracking-widest mb-1">How Buyer Uses VPIN</p>
          <div className="grid grid-cols-2 gap-2">
            <span>Futures VPIN spike = big move coming → get ready to BUY</span>
            <span>CE side {'>'} PE side = call sellers stressed → BUY CE</span>
            <span>PE side {'>'} CE side = put sellers stressed → BUY PE</span>
            <span>Both sides low = normal market → use Bob/Sellers tabs</span>
          </div>
        </div>
      </div>
    </div>
  )
}
