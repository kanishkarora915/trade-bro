export default function BobDashboard({ state }: { state: any }) {
  const bob = (state as any).bob_signal || { signal: 'WAIT', reason: 'Loading...', gates: {}, accumulation: {}, momentum_det: {}, context: {}, confluence_score: 0 }
  const { spot, atm, active_index } = state

  const isBuy = bob.signal === 'BUY' || bob.signal === 'STRONG BUY'
  const isWatch = bob.signal === 'WATCHLIST'

  const gateColor = (s: string) => s === 'GREEN' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : s === 'RED' ? 'bg-red-500/20 text-red-400 border-red-500/30' : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
  const gateIcon = (s: string) => s === 'GREEN' ? '✓' : s === 'RED' ? '✗' : '⚠'

  return (
    <div className="h-full flex flex-col bg-[#0a0f0a] overflow-hidden">
      {/* Header */}
      <div className="shrink-0 bg-emerald-950/30 border-b border-emerald-900/40 px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-400 to-green-600 rounded-lg flex items-center justify-center text-[11px] font-black text-black">B</div>
            <div>
              <h1 className="text-sm font-extrabold tracking-[.15em] text-emerald-400">BOB THE BUYER</h1>
              <p className="text-[9px] text-emerald-700">Option Buyer Signal Engine — Quality Over Quantity</p>
            </div>
          </div>
          <div className="flex items-center gap-5 text-[11px] font-mono">
            <span className="text-gray-500">SPOT <span className="text-white font-bold text-sm">{spot ? spot.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}</span></span>
            <span className="text-gray-500">ATM <span className="text-emerald-400 font-bold">{atm || '—'}</span></span>
            <span className="text-gray-500">IDX <span className="text-emerald-300 font-bold">{active_index}</span></span>
            {bob.ivr !== undefined && <span className="text-gray-500">IVR <span className={`font-bold ${bob.ivr < 30 ? 'text-emerald-400' : bob.ivr > 40 ? 'text-red-400' : 'text-yellow-400'}`}>{bob.ivr}%</span></span>}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Gate Status Strip */}
        <div className="flex gap-2">
          {[
            { label: 'IVR', data: bob.gates?.ivr },
            { label: 'GEX', data: bob.gates?.gex },
            { label: 'MOMENTUM', data: bob.gates?.momentum },
          ].map(g => {
            const status = g.data?.status || 'RED'
            return (
              <div key={g.label} className={`flex-1 border rounded-xl px-3 py-2.5 ${gateColor(status)}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-widest">{g.label}</span>
                  <span className="text-sm font-black">{gateIcon(status)}</span>
                </div>
                <p className="text-[9px] opacity-80 leading-snug">{g.data?.detail || 'No data'}</p>
                {g.label === 'GEX' && g.data?.net_gex !== undefined && (
                  <p className="text-[10px] font-mono font-bold mt-1">Net: {g.data.net_gex.toLocaleString('en-IN')}</p>
                )}
              </div>
            )
          })}
        </div>

        {/* Main Signal Card */}
        {isBuy ? (
          <div className={`border-2 rounded-2xl p-5 animate-pulse-slow ${
            bob.signal === 'STRONG BUY'
              ? 'border-emerald-400 bg-emerald-950/30 shadow-[0_0_30px_rgba(16,185,129,0.15)]'
              : 'border-emerald-600/50 bg-emerald-950/20'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className={`text-lg font-black tracking-wider ${bob.signal === 'STRONG BUY' ? 'text-emerald-300' : 'text-emerald-400'}`}>
                  {bob.signal === 'STRONG BUY' ? '⚡' : '▲'} {bob.signal}
                </span>
                {bob.conviction && (
                  <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold border ${
                    bob.conviction === 'MAXIMUM' ? 'bg-emerald-400/20 text-emerald-300 border-emerald-400/40' :
                    bob.conviction === 'HIGH' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' :
                    'bg-yellow-500/15 text-yellow-400 border-yellow-500/30'
                  }`}>{bob.conviction}</span>
                )}
              </div>
              <span className="text-2xl font-black text-emerald-400">{bob.confluence_score}/6</span>
            </div>

            {/* Trade Details Grid */}
            <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-xs font-mono mb-4">
              <div className="flex justify-between"><span className="text-gray-500">INSTRUMENT</span><span className="text-white font-bold">{bob.instrument}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">DIRECTION</span><span className="text-emerald-400 font-bold">{bob.direction}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">STRIKE</span><span className="text-emerald-300 font-bold text-sm">{bob.strike}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">ENTRY</span><span className="text-white font-bold text-sm">₹{bob.entry}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">STOP LOSS</span><span className="text-red-400 font-bold">₹{bob.stop_loss} (-40%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">TARGET 1</span><span className="text-emerald-400 font-bold">₹{bob.target1} (+80%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">TARGET 2</span><span className="text-emerald-300 font-bold">₹{bob.target2} (+150%)</span></div>
              <div className="flex justify-between"><span className="text-gray-500">LOTS</span><span className="text-white font-bold">{bob.lots}</span></div>
            </div>

            {/* Reason */}
            <div className="bg-black/30 rounded-xl p-3 mb-3">
              <p className="text-[10px] text-emerald-700 uppercase tracking-widest mb-1 font-bold">Why This Trade</p>
              <p className="text-[11px] text-gray-300 leading-relaxed">{bob.reason}</p>
            </div>

            {/* Fired Detectors */}
            {bob.fired?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {bob.fired.map((f: string, i: number) => (
                  <span key={i} className="text-[9px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 px-2 py-0.5 rounded-full font-bold">{f}</span>
                ))}
              </div>
            )}
          </div>
        ) : isWatch ? (
          <div className="border border-yellow-600/30 bg-yellow-950/15 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-lg font-black text-yellow-400">👁 WATCHLIST</span>
              <span className="text-yellow-500 text-sm font-mono font-bold">{bob.confluence_score}/6</span>
            </div>
            <p className="text-[11px] text-yellow-300/80 leading-relaxed mb-3">{bob.reason}</p>
            {bob.missing?.length > 0 && (
              <div>
                <p className="text-[9px] text-yellow-600 uppercase tracking-widest mb-1 font-bold">Still Need</p>
                <div className="flex flex-wrap gap-1.5">
                  {bob.missing.map((m: string, i: number) => (
                    <span key={i} className="text-[9px] bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 px-2 py-0.5 rounded-full">{m}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="border border-gray-700/50 bg-gray-900/50 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-lg font-black text-gray-500">⏸ WAIT</span>
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed">{bob.reason}</p>
            {bob.watch_for && (
              <p className="text-[10px] text-emerald-600 mt-2">Watch for: {typeof bob.watch_for === 'string' ? bob.watch_for : ''}</p>
            )}
          </div>
        )}

        {/* Position Sizing Card */}
        {bob.position && (
          <div className="border border-emerald-800/30 bg-emerald-950/10 rounded-xl p-4">
            <p className="text-[10px] text-emerald-600 uppercase tracking-widest mb-2 font-bold">Position Sizing</p>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-[9px] text-gray-500">LOTS</p>
                <p className="text-lg font-black text-emerald-400">{bob.position.lots}</p>
                <p className="text-[9px] text-gray-600">× {bob.position.lot_size} qty</p>
              </div>
              <div>
                <p className="text-[9px] text-gray-500">CAPITAL USED</p>
                <p className="text-lg font-black text-white">₹{(bob.position.capital_used || 0).toLocaleString('en-IN')}</p>
                <p className="text-[9px] text-gray-600">of ₹4,00,000</p>
              </div>
              <div>
                <p className="text-[9px] text-gray-500">MAX LOSS</p>
                <p className="text-lg font-black text-red-400">₹{(bob.position.max_loss || 0).toLocaleString('en-IN')}</p>
                <p className="text-[9px] text-gray-600">2% risk cap</p>
              </div>
            </div>
          </div>
        )}

        {/* Accumulation + Momentum Detectors */}
        {(Object.keys(bob.accumulation || {}).length > 0 || Object.keys(bob.momentum_det || {}).length > 0) && (
          <div className="grid grid-cols-2 gap-3">
            {/* Accumulation */}
            <div className="border border-gray-800 rounded-xl p-3">
              <p className="text-[9px] text-blue-400 uppercase tracking-widest mb-2 font-bold">Accumulation (need 2/3)</p>
              {Object.values(bob.accumulation || {}).map((d: any, i: number) => (
                <div key={i} className="flex items-center gap-2 py-1 text-[10px]">
                  <span className={`w-2 h-2 rounded-full ${d.fired ? 'bg-emerald-400' : 'bg-gray-700'}`} />
                  <span className={d.fired ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{d.name}</span>
                  {d.fired && <span className="text-gray-500 ml-auto text-[9px]">{d.status}</span>}
                </div>
              ))}
            </div>

            {/* Momentum */}
            <div className="border border-gray-800 rounded-xl p-3">
              <p className="text-[9px] text-purple-400 uppercase tracking-widest mb-2 font-bold">Momentum (need 2/3)</p>
              {Object.values(bob.momentum_det || {}).map((d: any, i: number) => (
                <div key={i} className="flex items-center gap-2 py-1 text-[10px]">
                  <span className={`w-2 h-2 rounded-full ${d.fired ? 'bg-emerald-400' : 'bg-gray-700'}`} />
                  <span className={d.fired ? 'text-emerald-400 font-bold' : 'text-gray-600'}>{d.name}</span>
                  {d.fired && <span className="text-gray-500 ml-auto text-[9px]">{d.status}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Context Boosters */}
        {Object.keys(bob.context || {}).length > 0 && (
          <div className="border border-gray-800 rounded-xl p-3">
            <p className="text-[9px] text-cyan-400 uppercase tracking-widest mb-2 font-bold">Context Boosters</p>
            <div className="grid grid-cols-2 gap-1">
              {Object.values(bob.context || {}).map((d: any, i: number) => (
                <div key={i} className="flex items-center gap-2 py-0.5 text-[10px]">
                  <span className={`w-1.5 h-1.5 rounded-full ${d.fired ? 'bg-cyan-400' : 'bg-gray-700'}`} />
                  <span className={d.fired ? 'text-cyan-400' : 'text-gray-600'}>{d.name}</span>
                  {d.metric && d.fired && <span className="text-gray-600 ml-auto text-[9px]">{d.metric}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rules — Always Visible */}
        <div className="border border-red-900/20 bg-red-950/10 rounded-xl p-3">
          <p className="text-[9px] text-red-500 uppercase tracking-widest mb-1.5 font-bold">Non-Negotiable Rules</p>
          <div className="grid grid-cols-2 gap-1 text-[9px] text-red-400/70">
            <span>• Capital: ₹4,00,000</span>
            <span>• Max Risk: ₹8,000 (2%)</span>
            <span>• Hard SL: 40% premium drop</span>
            <span>• Never average losers</span>
            <span>• Exit after 30 min no movement</span>
            <span>• Silence is valid output</span>
          </div>
        </div>
      </div>
    </div>
  )
}
