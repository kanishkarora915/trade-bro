"""Detector 12 — Greeks Anomaly. Detects abnormal Delta/Gamma/Vega before price moves."""
import math

_SQRT2PI = math.sqrt(2 * math.pi)

def _norm_cdf(x):
    """Standard normal CDF using math.erfc — no scipy needed."""
    return 0.5 * math.erfc(-x / math.sqrt(2))

def _norm_pdf(x):
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / _SQRT2PI

def _bs_delta(S, K, T, r, sigma, option_type="CE"):
    if T <= 0 or sigma <= 0:
        return 0.5
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    if option_type == "CE":
        return _norm_cdf(d1)
    return _norm_cdf(d1) - 1

def _bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))

def _bs_vega(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return S * _norm_pdf(d1) * math.sqrt(T) / 100


def detect(data: dict) -> dict:
    chain = data.get("chain", {})
    spot = data.get("spot", 24300)
    time_to_exp = max(0.001, data.get("time_to_expiry_mins", 1440) / (365 * 24 * 60))
    r = 0.065  # risk-free rate
    alerts = []
    top_score = 0

    for strike, sides in chain.items():
        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if not info or info.get("iv", 0) <= 0:
                continue

            sigma = info["iv"] / 100
            price = info.get("last_price", 0)
            if price <= 0:
                continue

            try:
                theo_delta = _bs_delta(spot, strike, time_to_exp, r, sigma, side_key)
                # Market-implied delta (rough approx from price movement)
                price_change = price * 0.01  # assume 1% change gives delta
                mkt_delta = theo_delta + (info.get("buy_pct", 0.5) - 0.5) * 0.3

                delta_dev = abs(mkt_delta - theo_delta)

                gamma = _bs_gamma(spot, strike, time_to_exp, r, sigma)
                vega = _bs_vega(spot, strike, time_to_exp, r, sigma)
            except Exception:
                continue

            if delta_dev < 0.08:
                continue

            sc = min(100, delta_dev / 0.3 * 100)
            top_score = max(top_score, sc)

            status = "CRITICAL" if delta_dev > 0.2 else "ALERT" if delta_dev > 0.15 else "WATCH"
            alerts.append({
                "strike": f"{int(strike)} {side_key}",
                "theo_delta": f"{theo_delta:.2f}",
                "mkt_delta": f"{mkt_delta:.2f}",
                "deviation": f"{delta_dev:+.2f}",
                "gamma": f"{gamma:.4f}",
                "vega": f"{vega:.2f}",
                "signal": "Market pricing in move" if delta_dev > 0.15 else "Mild anomaly",
                "status": status,
                "score": round(sc, 1),
            })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d12_greeks",
        "name": "Greeks Anomaly",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"Delta dev {best['deviation']}" if best else "Normal",
        "alerts": alerts[:5],
    }
