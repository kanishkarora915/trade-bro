"""Data Aggregator — per-user: pulls real Kite data, runs 17 detectors."""
import asyncio
import time
from datetime import datetime
from kite_client import KiteClient
from detectors import ALL_DETECTORS
from confluence_engine import calculate
from brain_signal import generate


class UserAggregator:
    """One aggregator per authenticated user session."""

    def __init__(self, kite: KiteClient):
        self.kite = kite
        self.latest_data: dict = {}
        self.detector_results: dict = {}
        self.confluence: dict = {"score": 0, "status": "NEUTRAL", "color": "grey", "direction": "NEUTRAL", "time_multiplier": 1, "is_expiry_day": False, "breakdown": {}, "firing": [], "timestamp": ""}
        self.brain: dict = {"active": False, "score": 0, "direction": "NEUTRAL", "primary": None, "secondary": None, "exit_rules": [], "firing": []}
        self.alert_log: list[dict] = []
        self._prev_score = 0
        self._last_fetch = 0
        self._error: str = ""

    async def run_cycle(self) -> dict:
        try:
            # Fetch live data from Kite
            ltp_data = await self.kite.get_ltp(["NSE:NIFTY 50", "NSE:NIFTY BANK"])
            nifty_ltp = 0
            bn_ltp = 0
            for k, v in ltp_data.items():
                if "NIFTY 50" in k:
                    nifty_ltp = v.get("last_price", 0)
                if "NIFTY BANK" in k:
                    bn_ltp = v.get("last_price", 0)

            if nifty_ltp <= 0:
                self._error = "Could not fetch Nifty price"
                return self.get_state()

            chain_data = await self.kite.build_option_chain(nifty_ltp)

            # Build data structure for detectors
            self.latest_data = {
                "spot": nifty_ltp,
                "atm": chain_data["atm"],
                "chain": chain_data["chain"],
                "trade_log": [],
                "sweep_events": [],
                "skew_history": [],
                "banknifty": {
                    "nifty_change_pct": 0,
                    "expected_bn_change_pct": 0,
                    "actual_bn_change_pct": 0,
                },
                "fii_dii": {"fii_net_cr": 0, "dii_net_cr": 0},
                "max_pain": chain_data["atm"],
                "depth_map": {},
                "expiry_date": chain_data.get("expiry", ""),
                "is_expiry_day": False,
                "time_to_expiry_mins": 1440,
                "trend": 0,
                "timestamp": datetime.now().isoformat(),
            }

            # Calculate max pain from chain
            chain = chain_data["chain"]
            strikes_list = sorted(chain.keys())
            if strikes_list:
                max_pain_losses = {}
                for mp in strikes_list:
                    total_loss = 0
                    for s in strikes_list:
                        ce = chain[s].get("CE")
                        pe = chain[s].get("PE")
                        ce_oi = ce["oi"] if ce else 0
                        pe_oi = pe["oi"] if pe else 0
                        if mp > s:
                            total_loss += (mp - s) * ce_oi
                        elif mp < s:
                            total_loss += (s - mp) * pe_oi
                    max_pain_losses[mp] = total_loss
                if max_pain_losses:
                    self.latest_data["max_pain"] = min(max_pain_losses, key=max_pain_losses.get)

                # Build depth map
                for s in strikes_list:
                    ce = chain[s].get("CE") or {}
                    pe = chain[s].get("PE") or {}
                    self.latest_data["depth_map"][s] = {
                        "CE": ce.get("bid_qty", 0) + ce.get("ask_qty", 0),
                        "PE": pe.get("bid_qty", 0) + pe.get("ask_qty", 0),
                    }

            # Run all 17 detectors
            self.detector_results = {}
            for det_id, detect_fn in ALL_DETECTORS.items():
                try:
                    self.detector_results[det_id] = detect_fn(self.latest_data)
                except Exception as e:
                    self.detector_results[det_id] = {
                        "id": det_id, "name": det_id, "score": 0,
                        "status": "NORMAL", "metric": f"Error", "alerts": [],
                    }

            # Confluence score
            self.confluence = calculate(self.detector_results, is_expiry_day=self.latest_data.get("is_expiry_day", False))

            # Brain signal
            self.brain = generate(self.confluence, self.detector_results, self.latest_data)

            # Alert tracking
            score = self.confluence.get("score", 0)
            if score >= 76 and self._prev_score < 76:
                self.alert_log.append({
                    "type": "SIGNAL",
                    "time": datetime.now().isoformat(),
                    "message": f"CONFLUENCE {self.confluence['status']} — Score {score:.0f} — {self.confluence['direction']}",
                })
            for det_id, result in self.detector_results.items():
                if result.get("status") in ("CRITICAL", "ALERT"):
                    for a in result.get("alerts", [])[:1]:
                        self.alert_log.append({
                            "type": result["status"],
                            "time": datetime.now().isoformat(),
                            "message": f"{result.get('name', det_id)} — {result.get('metric', '')}",
                        })
            self.alert_log = self.alert_log[-100:]
            self._prev_score = score
            self._error = ""
            self._last_fetch = time.time()

        except Exception as e:
            self._error = str(e)[:200]

        return self.get_state()

    def get_state(self) -> dict:
        return {
            "spot": self.latest_data.get("spot", 0),
            "atm": self.latest_data.get("atm", 0),
            "detectors": self.detector_results,
            "confluence": self.confluence,
            "brain": self.brain,
            "alert_log": self.alert_log[-20:],
            "strike_map": self.detector_results.get("d06_confluence_map", {}).get("strike_map", []),
            "error": self._error,
            "last_fetch": self._last_fetch,
            "timestamp": datetime.now().isoformat(),
        }


# Store aggregators per session
user_aggregators: dict[str, UserAggregator] = {}


def get_or_create_aggregator(session_id: str, kite: KiteClient) -> UserAggregator:
    if session_id not in user_aggregators:
        user_aggregators[session_id] = UserAggregator(kite)
    return user_aggregators[session_id]


def remove_aggregator(session_id: str):
    user_aggregators.pop(session_id, None)
