"""Telegram Alert System — Push BUY signals, EXIT alerts, daily P&L to Telegram.

Setup: Set env vars TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID on Render.
Create bot via @BotFather on Telegram, get chat_id by messaging bot and checking /getUpdates.
"""

import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_URL = "https://api.telegram.org/bot{token}/sendMessage"

_last_signal_sent: str = ""  # prevent duplicate sends
_last_alert_sent: float = 0
ALERT_COOLDOWN = 60  # 1 min between same-type alerts


async def send(text: str, parse_mode: str = "HTML") -> bool:
    """Send a Telegram message. Returns True if sent."""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(API_URL.format(token=BOT_TOKEN), json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
            return r.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM] Send error: {e}")
        return False


async def send_buy_signal(signal: str, trade: dict, reason: str, votes: dict, conviction: float):
    """Send BUY/STRONG BUY signal to Telegram."""
    global _last_signal_sent
    key = f"{signal}_{trade.get('strike', '')}"
    if key == _last_signal_sent:
        return  # already sent this exact signal
    _last_signal_sent = key

    now = datetime.now(IST).strftime("%H:%M:%S")
    emoji = "⚡" if signal == "STRONG BUY" else "🟢"

    text = f"""
{emoji} <b>{signal}</b> — {trade.get('strike', '')}

<b>Entry:</b> ₹{trade.get('entry', 0)}
<b>Stop Loss:</b> ₹{trade.get('stop_loss', 0)} (15%)
<b>Target 1:</b> ₹{trade.get('target1', 0)} (+30%)
<b>Target 2:</b> ₹{trade.get('target2', 0)} (+60%)
<b>Lots:</b> {trade.get('lots', 0)} × {trade.get('lot_size', 0)} qty
<b>Capital:</b> ₹{trade.get('capital_used', 0):,}
<b>Max Loss:</b> ₹{trade.get('max_loss', 0):,}

<b>Why:</b> {reason[:150]}
<b>Votes:</b> Bull {votes.get('bullish', 0)} vs Bear {votes.get('bearish', 0)}
<b>Conviction:</b> {conviction}
<b>Time:</b> {now} IST

#TradeBro #CommandCenter
""".strip()
    await send(text)


async def send_exit_alert(alert_type: str, msg: str, action: str, pnl_pct: float = 0):
    """Send EXIT/SL/TARGET alert to Telegram."""
    global _last_alert_sent
    import time
    if time.time() - _last_alert_sent < ALERT_COOLDOWN:
        return
    _last_alert_sent = time.time()

    emoji = "🚨" if "CRITICAL" in alert_type or "SL" in alert_type else "⚠️" if "WARNING" in alert_type else "✅"
    now = datetime.now(IST).strftime("%H:%M:%S")

    text = f"""
{emoji} <b>{alert_type}</b>

{msg}

<b>Action:</b> {action}
<b>P&L:</b> {pnl_pct:+.1f}%
<b>Time:</b> {now} IST

#TradeBro #Alert
""".strip()
    await send(text)


async def send_daily_report(trades: list, total_pnl: float, win_rate: float, capital: int):
    """Send end-of-day P&L summary."""
    now = datetime.now(IST)
    date = now.strftime("%d %b %Y")
    emoji = "📈" if total_pnl >= 0 else "📉"

    trade_lines = []
    for t in trades[-10:]:
        pnl = t.get("pnl_pct", 0)
        icon = "✅" if pnl > 0 else "❌" if pnl < 0 else "⏸"
        trade_lines.append(f"{icon} {t.get('strike', '?')} — Entry ₹{t.get('entry', 0)} → {t.get('exit_reason', '?')} ({pnl:+.1f}%)")

    trades_text = "\n".join(trade_lines) if trade_lines else "No trades today"

    text = f"""
{emoji} <b>DAILY REPORT — {date}</b>

<b>Total P&L:</b> ₹{total_pnl:+,.0f} ({total_pnl/capital*100:+.2f}%)
<b>Trades:</b> {len(trades)}
<b>Win Rate:</b> {win_rate:.0f}%
<b>Capital:</b> ₹{capital:,}

<b>Trades:</b>
{trades_text}

#TradeBro #DailyReport
""".strip()
    await send(text)


def is_configured() -> bool:
    return bool(BOT_TOKEN and CHAT_ID)
