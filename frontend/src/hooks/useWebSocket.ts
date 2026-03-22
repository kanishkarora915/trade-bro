import { useState, useEffect, useRef, useCallback } from 'react'

export interface TradeState {
  spot: number; atm: number
  detectors: Record<string, DetectorResult>
  confluence: ConfluenceResult
  brain: BrainSignal
  alert_log: AlertEntry[]
  strike_map: StrikeMapEntry[]
  error?: string; timestamp: string
}
export interface DetectorResult {
  id: string; name: string; score: number
  status: 'NORMAL' | 'WATCH' | 'ALERT' | 'CRITICAL'
  metric: string; alerts: any[]; direction?: string; strike_map?: StrikeMapEntry[]
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
export interface AlertEntry { type: string; time: string; message: string; score?: number; direction?: string; detector?: string }
export interface StrikeMapEntry { strike: number; ce_heat: number; pe_heat: number; net: number; label: string; is_atm: boolean }

const EMPTY: TradeState = {
  spot: 0, atm: 0, detectors: {},
  confluence: { score: 0, status: 'NEUTRAL', color: 'grey', direction: 'NEUTRAL', time_multiplier: 1, is_expiry_day: false, breakdown: {}, firing: [], timestamp: '' },
  brain: { active: false, score: 0, direction: 'NEUTRAL', primary: null, secondary: null, exit_rules: [], firing: [] },
  alert_log: [], strike_map: [], timestamp: '',
}

export function useWebSocket(sessionId: string | null) {
  const [state, setState] = useState<TradeState>(EMPTY)
  const [connected, setConnected] = useState(false)
  const [latency, setLatency] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const timer = useRef<number>()
  const pingTime = useRef(0)

  const connect = useCallback(() => {
    if (!sessionId) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_API_URL ? new URL(import.meta.env.VITE_API_URL).host : window.location.host
    const ws = new WebSocket(`${protocol}//${host}/ws/${sessionId}`)

    ws.onopen = () => {
      setConnected(true)
      // Start ping loop
      const ping = () => {
        if (ws.readyState === 1) {
          pingTime.current = performance.now()
          ws.send('ping')
        }
      }
      timer.current = window.setInterval(ping, 10000)
      ping()
    }
    ws.onmessage = (ev) => {
      if (ev.data === 'pong') {
        setLatency(Math.round(performance.now() - pingTime.current))
        return
      }
      try {
        const data = JSON.parse(ev.data)
        if (data.spot !== undefined) setState(data)
      } catch {}
    }
    ws.onclose = () => {
      setConnected(false)
      clearInterval(timer.current)
      setTimeout(connect, 3000)
    }
    ws.onerror = () => ws.close()
    wsRef.current = ws
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return
    connect()
    return () => {
      wsRef.current?.close()
      clearInterval(timer.current)
    }
  }, [sessionId, connect])

  return { state, connected, latency }
}
