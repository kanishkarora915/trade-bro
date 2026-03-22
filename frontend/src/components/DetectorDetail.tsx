import type { DetectorResult } from '../hooks/useWebSocket'

const STATUS_CLR: Record<string, string> = {
  NORMAL: 'text-tb-muted', WATCH: 'text-neon-blue', ALERT: 'text-neon-orange', CRITICAL: 'text-neon-red'
}
const STATUS_BG: Record<string, string> = {
  NORMAL: 'bg-tb-muted/10', WATCH: 'bg-blue-950/20', ALERT: 'bg-orange-950/20', CRITICAL: 'bg-red-950/20'
}

// Full descriptions and methodology per detector
const DETECTOR_INFO: Record<string, { description: string; methodology: string; thresholds: string[]; whatItMeans: string }> = {
  'd01_uoa': {
    description: 'Unusual Options Activity — detects volume spikes 3x+ above the 5-day average on any strike.',
    methodology: 'Compares current volume on each CE/PE strike against its 5-day average volume. A spike ratio of 3x+ triggers detection.',
    thresholds: ['3x-7x = WATCH (score 0-44)', '7x-12x = ALERT (score 44-100)', '12x+ = CRITICAL (score 100)'],
    whatItMeans: 'Volume spikes indicate someone knows something. When volume suddenly jumps 5x-10x normal, institutional players are positioning aggressively. Follow the money.',
  },
  'd02_order_flow': {
    description: 'Order Flow Imbalance — distinguishes aggressive BUYING vs SELLING using buy/sell quantity ratios.',
    methodology: 'Uses Kite WebSocket total_buy_quantity / total_sell_quantity per instrument to calculate real buy-side percentage. High buy% on CE = bullish flow. High sell% on PE (low buy%) = bearish flow.',
    thresholds: ['CE buy% 65-80% = ALERT (bullish imbalance)', 'CE buy% 80%+ = CRITICAL (strong bullish flow)', 'PE sell% 65-80% = ALERT (selling pressure)', 'PE sell% 80%+ = CRITICAL (heavy selling)'],
    whatItMeans: 'When 80%+ of order flow is on one side, market makers are being overwhelmed. This often precedes a directional move within minutes.',
  },
  'd03_sweep': {
    description: 'Strike Ladder Sweep — detects buying across 3+ consecutive strikes within 60 seconds.',
    methodology: 'Monitors real-time tick data for rapid volume bursts (100+ lots) across sequential strikes. When 3+ consecutive strikes show coordinated buying within 60s, it flags a sweep.',
    thresholds: ['3 strikes = WATCH (score 55-70)', '4+ strikes = CRITICAL (score 85-100)', 'Total lots factor adds bonus score'],
    whatItMeans: 'A sweep means an institution is buying everything available across strikes — they want maximum exposure NOW. This is the most reliable signal for an imminent directional move.',
  },
  'd04_iv_divergence': {
    description: 'IV Divergence — finds strikes where IV deviates from the expected volatility smile curve.',
    methodology: 'Fits a quadratic curve (vol smile) to IVs across strikes, then finds outliers. Positive deviation = hidden demand. Negative = IV suppressed.',
    thresholds: ['1.5-2.5% deviation = WATCH', '2.5-3.5% deviation = ALERT', '3.5%+ deviation = CRITICAL'],
    whatItMeans: 'When a specific strike\'s IV is abnormally high vs the smile curve, someone is paying up for that strike. Hidden call demand = bullish bet. Hidden put demand = bearish bet.',
  },
  'd05_velocity': {
    description: 'T&S Velocity Engine — tracks contracts/minute spikes relative to 20-minute baseline.',
    methodology: 'Calculates contracts traded in the last 60 seconds per strike and compares to the 20-minute average. A 3x+ velocity spike triggers detection.',
    thresholds: ['3x-10x velocity = WATCH (score 30-85)', '10x+ velocity = CRITICAL (score 85-100)'],
    whatItMeans: 'Sudden acceleration in trading velocity means urgent positioning. When velocity spikes 10x, someone is deploying capital with urgency — they have a time-sensitive view.',
  },
  'd06_confluence_map': {
    description: 'Multi-Strike Confluence Map — aggregates volume, flow, and IV signals across all strikes to determine market direction.',
    methodology: 'For each strike: scores CE and PE heat from volume spikes (>3x), buy flow (>65%), and IV (>14%). Sums CE vs PE heat across all strikes. Higher CE heat = BULLISH, higher PE heat = BEARISH.',
    thresholds: ['CE-PE diff < 3 = NEUTRAL', 'Diff 3-8 = WATCH', 'Diff 8+ = ALERT'],
    whatItMeans: 'This is the master direction indicator. When CE heat significantly exceeds PE heat (or vice versa), the smart money is clearly positioned in one direction.',
  },
  'd07_block_print': {
    description: 'Block Print / Dark Trade Identifier — catches single massive trades (500+ lots) that indicate institutional activity.',
    methodology: 'Monitors Kite WebSocket last_traded_quantity. Trades of 500+ lots (12,500+ shares for Nifty) are flagged as block prints. 2000+ lots = dark prints.',
    thresholds: ['500-2000 lots = ALERT / BLOCK PRINT (score 40-90)', '2000+ lots = CRITICAL / DARK PRINT (score 90-100)'],
    whatItMeans: 'A 500+ lot trade is ₹5-50 lakh+ in a single click. This is not retail. When you see 2000+ lots (dark print), a large fund is making a big bet.',
  },
  'd08_repeat_buyer': {
    description: 'Repeat Buyer Fingerprint — finds stealth accumulation where the same lot size repeats on a strike.',
    methodology: 'Groups trades by strike+side, then clusters by size (within 20% tolerance). If 3+ trades of similar size appear on the same strike, it flags accumulation.',
    thresholds: ['3-4 repeats = WATCH / STEALTH BUY (score 40-80)', '5+ repeats = CRITICAL / CONFIRMED ACCUMULATION (score 80-100)'],
    whatItMeans: 'When someone buys 200 lots, then 200 again, then 195 again on the same strike — that\'s algorithmic accumulation. They\'re building a position without moving the market.',
  },
  'd09_skew_shift': {
    description: 'Put-Call Skew Shift — detects when call IV rises faster than put IV (or vice versa).',
    methodology: 'Tracks ATM CE vs PE implied volatility changes over time. When CE IV rises faster than PE IV = bullish skew shift. Reverse = bearish shift.',
    thresholds: ['0.5-1.5% diff = WATCH (shift starting)', '1.5%+ diff = CRITICAL (flip detected)'],
    whatItMeans: 'Skew shifts reveal directional demand before price moves. When traders pay more for calls vs puts, they\'re betting on upside. This often precedes the move by 5-15 minutes.',
  },
  'd10_bid_ask': {
    description: 'Bid-Ask Spread Widening — detects when market makers widen spreads as an early warning signal.',
    methodology: 'Compares current bid-ask spread to baseline spread for each option. Widening of 2x+ indicates market makers are de-risking.',
    thresholds: ['2x-3.5x widen = WATCH', '3.5x+ widen = ALERT'],
    whatItMeans: 'Market makers widen spreads when they sense a big move coming. Wide spreads = less liquidity = potential for sharp price swings. Use limit orders only.',
  },
  'd11_synthetic': {
    description: 'Synthetic Position Detector — detects CE buy + PE sell at same strike (synthetic long) or CE sell + PE buy (synthetic short).',
    methodology: 'From trade log, aggregates buy/sell volume per strike. If CE buying + PE selling both exceed 200 lots on the same strike with >50% correlation, it flags a synthetic position.',
    thresholds: ['50-70% correlation = ALERT / MEDIUM confidence', '70%+ correlation = CRITICAL / HIGH confidence'],
    whatItMeans: 'A synthetic long (buy CE + sell PE) gives the same payoff as buying futures but with leverage. Only institutions build these. Direction is confirmed when both legs are active.',
  },
  'd12_greeks': {
    description: 'Greeks Anomaly — detects abnormal Delta/Gamma/Vega deviation from Black-Scholes theoretical values.',
    methodology: 'Calculates theoretical delta using Black-Scholes and compares to market-implied delta (derived from buy_pct flow). Also computes gamma and vega for context.',
    thresholds: ['0.08-0.15 delta deviation = WATCH', '0.15-0.20 deviation = ALERT', '0.20+ deviation = CRITICAL'],
    whatItMeans: 'When market delta deviates from theory, the market is pricing in information not visible in the model. Large delta anomalies often precede sharp directional moves.',
  },
  'd13_news_mismatch': {
    description: 'News-Price Reaction Mismatch — when market reacts opposite to expected news impact.',
    methodology: 'Compares news sentiment (from feeds) with actual price reaction. If negative news should push market down but it goes up, flags "HIDDEN HAND WAS LONG".',
    thresholds: ['Any mismatch = ALERT (score 70)', 'Strong mismatch with trend confirmation = higher score'],
    whatItMeans: 'When market goes UP on bad news, smart money was already long. The news was "priced in" or someone has better information. Follow the actual price action, not the news.',
  },
  'd14_max_pain': {
    description: 'Max Pain & Expiry Tracker — tracks where option sellers want the market to close (minimum loss point).',
    methodology: 'Calculates OI-weighted total loss for all strikes. The strike with minimum total loss = max pain. Compares spot distance from max pain.',
    thresholds: ['0-75 pts from MP = NORMAL (sellers in control)', '75-150 pts = WATCH (moderate deviation)', '150+ pts = ALERT/CRITICAL (buyers overpowering)'],
    whatItMeans: 'On expiry day, market tends to drift toward max pain as option sellers protect positions. If market is 200+ pts away, either a strong trend will continue OR a violent reversal is coming.',
  },
  'd15_correlation': {
    description: 'Nifty-BankNifty Correlation Break — detects when BankNifty deviates from its normal 1.5x relationship with Nifty.',
    methodology: 'BankNifty normally moves 1.5x Nifty. When actual BankNifty change deviates from expected by >0.5%, a divergence is flagged.',
    thresholds: ['0.5-1.0% deviation = WATCH', '1.0%+ deviation = ALERT'],
    whatItMeans: 'Correlation breaks indicate sector-specific events. If BankNifty underperforms, something is wrong in banking. If it outperforms, banking is leading the rally.',
  },
  'd16_vacuum': {
    description: 'Liquidity Vacuum Detector — finds empty zones in the order book where price can move rapidly.',
    methodology: 'Scans depth map for zones where total bid+ask depth drops below 10% of average. Consecutive vacuum strikes form a vacuum zone.',
    thresholds: ['30+ pt vacuum zone = WATCH', 'Vacuum zone at spot boundary = ALERT/CRITICAL'],
    whatItMeans: 'A vacuum zone is like a gap in the floor — if price enters it, there\'s nothing to stop it until the other side. If spot is near a vacuum boundary, a fast 30-100 pt move can happen instantly.',
  },
  'd17_fii_dii': {
    description: 'FII vs DII Battle Tracker — compares Foreign Institutional Investor vs Domestic Institutional Investor net activity.',
    methodology: 'Fetches real FII/DII data from NSE. FII buying + market up = momentum confirmed. FII selling + DII buying = equilibrium. FII heavy selling = bearish pressure.',
    thresholds: ['FII >2000 Cr buying = CRITICAL bullish', 'FII >2000 Cr selling = CRITICAL bearish', 'FII selling > 1.2x DII buying = floor weakening'],
    whatItMeans: 'FII controls the trend, DII provides the floor. When FII is buying heavily, go with the flow. When FII sells and DII supports, market consolidates. When DII stops buying — crash ahead.',
  },
}

export default function DetectorDetail({ detector, onClose }: { detector: DetectorResult; onClose: () => void }) {
  const info = DETECTOR_INFO[detector.id] || {
    description: detector.name,
    methodology: 'Analyzing market data for anomalies.',
    thresholds: ['WATCH → ALERT → CRITICAL'],
    whatItMeans: 'Higher scores indicate stronger signals.',
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-tb-card border border-tb-border rounded-2xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-lg font-bold text-tb-text">{detector.name}</h2>
            <p className="text-[11px] text-tb-muted mt-0.5">{info.description}</p>
          </div>
          <button onClick={onClose} className="text-tb-muted hover:text-tb-text text-xl px-2 ml-4">✕</button>
        </div>

        {/* Score + Status */}
        <div className="flex items-center gap-4 mb-4">
          <div className={`px-5 py-3 rounded-xl text-center ${STATUS_BG[detector.status]}`}>
            <p className="text-3xl font-black text-tb-text">{detector.score.toFixed(0)}</p>
            <p className="text-[9px] text-tb-muted uppercase">/ 100</p>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <span className={`text-sm font-bold ${STATUS_CLR[detector.status]}`}>{detector.status}</span>
              <span className="text-xs text-tb-text font-mono">{detector.metric}</span>
            </div>
            <div className="h-2.5 bg-tb-border rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-500 ${
                detector.status === 'CRITICAL' ? 'bg-neon-red' : detector.status === 'ALERT' ? 'bg-neon-orange' :
                detector.status === 'WATCH' ? 'bg-neon-blue' : 'bg-tb-muted/40'
              }`} style={{ width: `${detector.score}%` }} />
            </div>
          </div>
        </div>

        {/* What This Means */}
        <div className="bg-tb-bg border border-tb-border rounded-xl p-4 mb-4">
          <h3 className="text-[10px] text-neon-cyan uppercase tracking-widest font-bold mb-1.5">What This Means</h3>
          <p className="text-[11px] text-tb-text leading-relaxed">{info.whatItMeans}</p>
        </div>

        {/* Methodology */}
        <div className="bg-tb-bg border border-tb-border rounded-xl p-4 mb-4">
          <h3 className="text-[10px] text-neon-yellow uppercase tracking-widest font-bold mb-1.5">How It Calculates</h3>
          <p className="text-[11px] text-tb-muted leading-relaxed">{info.methodology}</p>
        </div>

        {/* Thresholds */}
        <div className="bg-tb-bg border border-tb-border rounded-xl p-4 mb-4">
          <h3 className="text-[10px] text-neon-orange uppercase tracking-widest font-bold mb-1.5">Scoring Thresholds</h3>
          <div className="space-y-1">
            {info.thresholds.map((t, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px]">
                <span className="text-neon-orange mt-0.5 shrink-0">▸</span>
                <span className="text-tb-muted">{t}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Alerts / Data */}
        {detector.alerts && detector.alerts.length > 0 ? (
          <div>
            <h3 className="text-[10px] text-neon-green uppercase tracking-widest font-bold mb-2">Live Data ({detector.alerts.length} alerts)</h3>
            <div className="space-y-2">
              {detector.alerts.map((alert: any, i: number) => (
                <div key={i} className={`border rounded-xl p-3 ${
                  alert.status === 'CRITICAL' ? 'border-neon-red/30 bg-red-950/10' :
                  alert.status === 'ALERT' ? 'border-neon-orange/30 bg-orange-950/10' :
                  'border-tb-border bg-tb-bg'
                }`}>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1.5 text-[11px] font-mono">
                    {Object.entries(alert).filter(([k]) => k !== 'score').map(([key, val]) => (
                      <div key={key} className="flex flex-col">
                        <span className="text-tb-muted/60 uppercase text-[8px] tracking-wider">{key.replace(/_/g, ' ')}</span>
                        <span className={`text-tb-text font-medium ${
                          key === 'status' ? STATUS_CLR[val as string] || '' :
                          key === 'label' || key === 'signal' || key === 'direction' || key === 'type' || key === 'pattern' ? 'text-neon-cyan font-bold' :
                          key === 'strike' ? 'text-neon-green' :
                          ''
                        }`}>{String(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="border border-tb-border rounded-xl p-6 text-center">
            <p className="text-tb-muted text-sm mb-1">No active alerts</p>
            <p className="text-[10px] text-tb-muted/50">
              Detector is in NORMAL state. {detector.score === 0
                ? 'No significant activity detected on any strike.'
                : `Score is ${detector.score.toFixed(0)} — below alert threshold.`
              }
            </p>
            {detector.id === 'd03_sweep' && <p className="text-[9px] text-tb-muted/40 mt-2">Sweep detection requires real-time tick data from Kite WebSocket. Active during market hours.</p>}
            {detector.id === 'd07_block_print' && <p className="text-[9px] text-tb-muted/40 mt-2">Block prints require live trade data. Large trades (500+ lots) are detected from tick-by-tick WebSocket feed.</p>}
            {detector.id === 'd08_repeat_buyer' && <p className="text-[9px] text-tb-muted/40 mt-2">Repeat buyer patterns are detected from accumulated trade data during market hours.</p>}
            {detector.id === 'd17_fii_dii' && <p className="text-[9px] text-tb-muted/40 mt-2">FII/DII data is fetched from NSE. Data updates once per day (after market close).</p>}
          </div>
        )}
      </div>
    </div>
  )
}
