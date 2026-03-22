import { useState, useEffect, useRef, useCallback } from 'react'

export interface IndexState {
  index_id: string; name: string; spot: number; atm: number
  detectors: Record<string, DetectorResult>; confluence: ConfluenceResult
  brain: BrainSignal; strike_map: StrikeMapEntry[]; chain_summary: ChainRow[]
  error: string; last_fetch: number
}
export interface TradeState {
  active_index: string; indices: Record<string, IndexState>
  spots: Record<string, number>; alert_log: AlertEntry[]; flow_tape: FlowEntry[]
  spot: number; atm: number; detectors: Record<string, DetectorResult>
  confluence: ConfluenceResult; brain: BrainSignal; strike_map: StrikeMapEntry[]
  chain_summary: ChainRow[]; error?: string; timestamp: string
  ai_analysis?: AIAnalysis; signal_history?: SignalHistoryEntry[]
  last_signal?: BrainSignal | null; fii_dii?: FiiDiiData; ticker_active?: boolean
}
export interface DetectorResult {
  id: string; name: string; score: number
  status: 'NORMAL' | 'WATCH' | 'ALERT' | 'CRITICAL'
  metric: string; alerts: any[]; direction?: string
}
export interface ConfluenceResult {
  score: number; status: string; color: string; direction: string
  time_multiplier: number; is_expiry_day: boolean
  breakdown: Record<string, any>; firing: { name: string; metric: string; status: string }[]
  timestamp: string
}
export interface BrainSignal {
  active: boolean; message?: string; score: number; strength?: string; direction: string
  primary: { action: string; strike: string; cmp: string; cmp_raw: number; target1: string; target2: string; stop_loss: string; time_limit: string } | null
  secondary: { action: string; strike: string; cmp: string; target: string; stop_loss: string } | null
  exit_rules: { rule: string; detail: string }[]
  firing: { name: string; metric: string; status: string }[]
  nifty_spot?: number; expiry?: string; timestamp?: string
}
export interface AIAnalysis {
  summary: string; analysis: string; bullets: string[]
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'MIXED'
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
  risk_notes: string[]; timestamp: string
}
export interface SignalHistoryEntry extends BrainSignal {
  index: string; recorded_at: string; spot_at_signal: number
}
export interface FiiDiiData {
  fii_net_cr: number; dii_net_cr: number; fii_buy?: number; fii_sell?: number
  dii_buy?: number; dii_sell?: number; date?: string; source?: string
}
export interface AlertEntry { type: string; time: string; message: string }
export interface StrikeMapEntry { strike: number; ce_heat: number; pe_heat: number; net: number; label: string; is_atm: boolean }
export interface ChainRow {
  strike: number; ce_ltp: number; ce_vol: number; ce_oi: number; ce_iv: number
  ce_bid: number; ce_ask: number; ce_oi_chg: number
  pe_ltp: number; pe_vol: number; pe_oi: number; pe_iv: number
  pe_bid: number; pe_ask: number; pe_oi_chg: number; is_atm: boolean
}
export interface FlowEntry {
  time: string; index: string; strike: string; price: number; volume: number; oi: number; type: 'BUY' | 'SELL' | 'NEUTRAL'
}

const EMPTY_CONF: ConfluenceResult = { score: 0, status: 'NEUTRAL', color: 'grey', direction: 'NEUTRAL', time_multiplier: 1, is_expiry_day: false, breakdown: {}, firing: [], timestamp: '' }
const EMPTY_BRAIN: BrainSignal = { active: false, score: 0, direction: 'NEUTRAL', primary: null, secondary: null, exit_rules: [], firing: [] }
const EMPTY: TradeState = {
  active_index: 'NIFTY', indices: {}, spots: {}, alert_log: [], flow_tape: [],
  spot: 0, atm: 0, detectors: {}, confluence: EMPTY_CONF, brain: EMPTY_BRAIN,
  strike_map: [], chain_summary: [], timestamp: '',
}

export function useWebSocket(sessionId: string | null) {
  const [state, setState] = useState<TradeState>(EMPTY)
  const [connected, setConnected] = useState(false)
  const [latency, setLatency] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const timer = useRef<number>()
  const pingT = useRef(0)

  const connect = useCallback(() => {
    if (!sessionId) return
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_URL ? new URL(import.meta.env.VITE_API_URL).host : window.location.host
    const ws = new WebSocket(`${proto}//${host}/ws/${sessionId}`)
    ws.onopen = () => {
      setConnected(true)
      const ping = () => { if (ws.readyState === 1) { pingT.current = performance.now(); ws.send('ping') } }
      timer.current = window.setInterval(ping, 8000)
      ping()
    }
    ws.onmessage = (ev) => {
      if (ev.data === 'pong') { setLatency(Math.round(performance.now() - pingT.current)); return }
      try { const d = JSON.parse(ev.data); if (d.spot !== undefined) setState(d) } catch {}
    }
    ws.onclose = () => { setConnected(false); clearInterval(timer.current); setTimeout(connect, 3000) }
    ws.onerror = () => ws.close()
    wsRef.current = ws
  }, [sessionId])

  const switchIndex = useCallback((idx: string) => {
    if (wsRef.current?.readyState === 1) wsRef.current.send(`switch:${idx}`)
  }, [])

  useEffect(() => {
    if (!sessionId) return
    connect()
    return () => { wsRef.current?.close(); clearInterval(timer.current) }
  }, [sessionId, connect])

  return { state, connected, latency, switchIndex }
}
