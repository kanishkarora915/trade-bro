import { useEffect, useRef } from 'react'
import type { ConfluenceResult } from './useWebSocket'

const ctx = typeof AudioContext !== 'undefined' ? new AudioContext() : null

function tone(freq: number, dur: number, type: OscillatorType = 'square') {
  if (!ctx) return
  const o = ctx.createOscillator()
  const g = ctx.createGain()
  o.type = type; o.frequency.value = freq; g.gain.value = 0.12
  g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur)
  o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + dur)
}

function bullish() { tone(880,0.12); setTimeout(()=>tone(1100,0.12),120); setTimeout(()=>tone(1320,0.25),240) }
function bearish() { tone(660,0.12,'sawtooth'); setTimeout(()=>tone(440,0.12,'sawtooth'),120); setTimeout(()=>tone(330,0.25,'sawtooth'),240) }
function critical() { for(let i=0;i<3;i++){setTimeout(()=>tone(1500,0.08),i*160);setTimeout(()=>tone(800,0.08),i*160+80)} }

export function useAlerts(c: ConfluenceResult) {
  const prev = useRef(0)
  useEffect(() => {
    const s = c.score, p = prev.current
    if (s >= 76 && p < 76) {
      c.direction === 'BULLISH' ? bullish() : bearish()
      if (Notification.permission === 'granted') new Notification('TRADE BRO', { body: `Score ${s.toFixed(0)} | ${c.direction}` })
      else if (Notification.permission !== 'denied') Notification.requestPermission()
    }
    if (s >= 86 && p < 86) critical()
    prev.current = s
  }, [c.score, c.direction])
}
