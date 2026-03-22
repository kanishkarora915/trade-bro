import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

# Server
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# License keys (20 users)
LICENSE_KEYS = {
    "TRADE-BRO-001": {"name": "User 1", "active": True},
    "TRADE-BRO-002": {"name": "User 2", "active": True},
    "TRADE-BRO-003": {"name": "User 3", "active": True},
    "TRADE-BRO-004": {"name": "User 4", "active": True},
    "TRADE-BRO-005": {"name": "User 5", "active": True},
    "TRADE-BRO-006": {"name": "User 6", "active": True},
    "TRADE-BRO-007": {"name": "User 7", "active": True},
    "TRADE-BRO-008": {"name": "User 8", "active": True},
    "TRADE-BRO-009": {"name": "User 9", "active": True},
    "TRADE-BRO-010": {"name": "User 10", "active": True},
    "TRADE-BRO-011": {"name": "User 11", "active": True},
    "TRADE-BRO-012": {"name": "User 12", "active": True},
    "TRADE-BRO-013": {"name": "User 13", "active": True},
    "TRADE-BRO-014": {"name": "User 14", "active": True},
    "TRADE-BRO-015": {"name": "User 15", "active": True},
    "TRADE-BRO-016": {"name": "User 16", "active": True},
    "TRADE-BRO-017": {"name": "User 17", "active": True},
    "TRADE-BRO-018": {"name": "User 18", "active": True},
    "TRADE-BRO-019": {"name": "User 19", "active": True},
    "TRADE-BRO-020": {"name": "User 20", "active": True},
    "KANISHK-MASTER-KEY": {"name": "Kanishk Arora (Admin)", "active": True},
}

# Nifty config
NIFTY_SYMBOL = "NIFTY 50"
BANKNIFTY_SYMBOL = "NIFTY BANK"
NIFTY_STRIKE_STEP = 50
OPTION_CHAIN_RANGE = 500

REFRESH_OPTION_CHAIN_SEC = 20  # faster refresh — 20s instead of 30s
REFRESH_PRICE_SEC = 5

# Session config
MAX_SESSIONS = 25
SESSION_TIMEOUT_HOURS = 12

# Detector weights
DETECTOR_WEIGHTS = {
    "d01_uoa": 12,
    "d02_order_flow": 12,
    "d03_sweep": 15,
    "d04_iv_divergence": 8,
    "d05_velocity": 10,
    "d06_confluence_map": 5,
    "d07_block_print": 10,
    "d08_repeat_buyer": 8,
    "d09_skew_shift": 6,
    "d10_bid_ask": 5,
    "d11_synthetic": 7,
    "d12_greeks": 6,
    "d13_news_mismatch": 4,
    "d14_max_pain": 4,
    "d15_correlation": 3,
    "d16_vacuum": 8,
    "d17_fii_dii": 3,
}
TOTAL_MAX_POINTS = sum(DETECTOR_WEIGHTS.values())
