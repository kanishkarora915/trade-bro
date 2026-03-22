import DetectorCard from './DetectorCard'
import type { DetectorResult } from '../hooks/useWebSocket'

const ORDER = [
  'd01_uoa','d02_order_flow','d03_sweep','d04_iv_divergence','d05_velocity',
  'd06_confluence_map','d07_block_print','d08_repeat_buyer','d09_skew_shift',
  'd10_bid_ask','d11_synthetic','d12_greeks','d13_news_mismatch','d14_max_pain',
  'd15_correlation','d16_vacuum','d17_fii_dii',
]

export default function IndicatorsPanel({ detectors, onDetectorClick }: {
  detectors: Record<string, DetectorResult>; onDetectorClick: (d: DetectorResult) => void
}) {
  const active = ORDER.filter(id => detectors[id]?.status !== 'NORMAL').length
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="text-[11px] font-bold text-neon-cyan uppercase tracking-widest">17 Detectors</h2>
        <span className="text-[10px] font-mono text-tb-muted">{active} active</span>
      </div>
      <div className="flex-1 overflow-y-auto pr-1 space-y-2">
        {ORDER.map(id => {
          const d = detectors[id]
          return d ? <DetectorCard key={id} d={d} onClick={() => onDetectorClick(d)} /> : null
        })}
      </div>
    </div>
  )
}
