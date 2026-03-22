import type { ChainRow } from '../hooks/useWebSocket'

export default function StrikeDetail({ chain, atm, onClose }: { chain: ChainRow[]; atm: number; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-tb-card border border-tb-border rounded-2xl p-5 max-w-6xl w-full max-h-[85vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-neon-cyan tracking-widest">FULL OPTION CHAIN — ATM {atm}</h2>
          <button onClick={onClose} className="text-tb-muted hover:text-tb-text text-xl px-2">✕</button>
        </div>

        {!chain || chain.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center py-12">
              <p className="text-tb-muted text-lg mb-2">Chain data loading...</p>
              <p className="text-tb-muted/50 text-xs">Option chain will appear once Kite API responds. This may take a few seconds on first load.</p>
              <p className="text-tb-muted/40 text-[10px] mt-3">If market is closed, last trading day data will show after the first data cycle (30s).</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-[10px] font-mono">
              <thead className="sticky top-0 bg-tb-card z-10">
                <tr className="text-tb-muted">
                  <th colSpan={7} className="text-center text-neon-green py-1 border-b border-tb-border">— CALLS —</th>
                  <th className="text-center py-1 border-b border-tb-border text-neon-cyan">STRIKE</th>
                  <th colSpan={7} className="text-center text-neon-red py-1 border-b border-tb-border">— PUTS —</th>
                </tr>
                <tr className="text-tb-muted/70 text-[9px]">
                  <th className="py-1 px-1 text-right">OI Chg</th>
                  <th className="py-1 px-1 text-right">OI</th>
                  <th className="py-1 px-1 text-right">Vol</th>
                  <th className="py-1 px-1 text-right">IV</th>
                  <th className="py-1 px-1 text-right">LTP</th>
                  <th className="py-1 px-1 text-right">Bid</th>
                  <th className="py-1 px-1 text-right">Ask</th>
                  <th className="py-1 px-1 text-center">⬤</th>
                  <th className="py-1 px-1 text-right">Bid</th>
                  <th className="py-1 px-1 text-right">Ask</th>
                  <th className="py-1 px-1 text-right">LTP</th>
                  <th className="py-1 px-1 text-right">IV</th>
                  <th className="py-1 px-1 text-right">Vol</th>
                  <th className="py-1 px-1 text-right">OI</th>
                  <th className="py-1 px-1 text-right">OI Chg</th>
                </tr>
              </thead>
              <tbody>
                {chain.map((r) => (
                  <tr key={r.strike} className={`border-b border-tb-border/30 hover:bg-tb-surface/30 ${
                    r.is_atm ? 'bg-neon-cyan/5 font-semibold' : ''
                  }`}>
                    <td className={`py-1 px-1 text-right ${r.ce_oi_chg > 0 ? 'text-neon-green' : r.ce_oi_chg < 0 ? 'text-neon-red' : 'text-tb-muted'}`}>
                      {r.ce_oi_chg > 0 ? '+' : ''}{(r.ce_oi_chg / 1000).toFixed(1)}K
                    </td>
                    <td className="py-1 px-1 text-right text-tb-text">{(r.ce_oi / 1000).toFixed(0)}K</td>
                    <td className="py-1 px-1 text-right text-tb-text">{r.ce_vol.toLocaleString()}</td>
                    <td className="py-1 px-1 text-right text-neon-yellow">{r.ce_iv > 0 ? r.ce_iv.toFixed(1) : '—'}</td>
                    <td className={`py-1 px-1 text-right font-semibold ${(r as any).ce_chg > 0 ? 'text-neon-green' : (r as any).ce_chg < 0 ? 'text-neon-red' : 'text-tb-text'}`}>
                      {r.ce_ltp > 0 ? r.ce_ltp.toFixed(1) : '—'}
                    </td>
                    <td className="py-1 px-1 text-right text-neon-green">{r.ce_bid || '—'}</td>
                    <td className="py-1 px-1 text-right text-neon-red">{r.ce_ask || '—'}</td>
                    <td className={`py-1 px-1 text-center font-bold ${r.is_atm ? 'text-neon-cyan' : 'text-tb-text'}`}>
                      {r.strike}
                    </td>
                    <td className="py-1 px-1 text-right text-neon-green">{r.pe_bid || '—'}</td>
                    <td className="py-1 px-1 text-right text-neon-red">{r.pe_ask || '—'}</td>
                    <td className={`py-1 px-1 text-right font-semibold ${(r as any).pe_chg > 0 ? 'text-neon-green' : (r as any).pe_chg < 0 ? 'text-neon-red' : 'text-tb-text'}`}>
                      {r.pe_ltp > 0 ? r.pe_ltp.toFixed(1) : '—'}
                    </td>
                    <td className="py-1 px-1 text-right text-neon-yellow">{r.pe_iv > 0 ? r.pe_iv.toFixed(1) : '—'}</td>
                    <td className="py-1 px-1 text-right text-tb-text">{r.pe_vol.toLocaleString()}</td>
                    <td className="py-1 px-1 text-right text-tb-text">{(r.pe_oi / 1000).toFixed(0)}K</td>
                    <td className={`py-1 px-1 text-right ${r.pe_oi_chg > 0 ? 'text-neon-green' : r.pe_oi_chg < 0 ? 'text-neon-red' : 'text-tb-muted'}`}>
                      {r.pe_oi_chg > 0 ? '+' : ''}{(r.pe_oi_chg / 1000).toFixed(1)}K
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
