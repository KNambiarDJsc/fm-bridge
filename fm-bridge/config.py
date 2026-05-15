"""
FM Trading Agency — Bridge Config
===================================
All configuration lives here.  Copy .env.example → .env and fill in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Zerodha ───────────────────────────────────────────────────
    api_key:      str = Field("", description="Zerodha API key (kite.trade/apps)")
    api_secret:   str = Field("", description="Zerodha API secret")

    # ── TOTP auto-login (store once, never type again) ────────────
    zerodha_user_id:   Optional[str] = Field(None, description="Zerodha user ID (e.g. ZG1234)")
    zerodha_password:  Optional[str] = Field(None, description="Zerodha login password")
    zerodha_totp_key:  Optional[str] = Field(None, description="Base32 TOTP secret from authenticator app")

    # ── Server ────────────────────────────────────────────────────
    bridge_host:  str = Field("0.0.0.0",  description="Bridge bind host")
    bridge_port:  int = Field(8002,        description="Bridge bind port")
    ws_port:      int = Field(8765,        description="WebSocket tick stream port")
    zmq_port:     int = Field(5555,        description="ZMQ pub socket port")

    # ── Cache ─────────────────────────────────────────────────────
    redis_url:    Optional[str] = Field(None, description="redis://localhost:6379 — leave blank for in-memory")
    cache_ttl_ltp:        int = Field(2,    description="LTP cache TTL seconds")
    cache_ttl_indicators: int = Field(60,   description="Indicator cache TTL seconds")
    cache_ttl_options:    int = Field(900,  description="Options chain cache TTL seconds (15 min)")
    cache_ttl_macro:      int = Field(3600, description="Macro context cache TTL seconds (1 hr)")

    # ── Scheduler ─────────────────────────────────────────────────
    options_fetch_time: str = Field("07:00", description="HH:MM IST — daily options chain batch pull")
    macro_fetch_time:   str = Field("09:00", description="HH:MM IST — daily macro context fetch")
    timezone:           str = Field("Asia/Kolkata")

    # ── Capital / risk defaults (for Capital Shield) ──────────────
    default_capital:     float = Field(1_000_000, description="Default trader capital ₹")
    daily_dd_limit_pct:  float = Field(1.0,  description="Daily drawdown kill-switch %")
    weekly_dd_limit_pct: float = Field(3.0,  description="Weekly drawdown limit %")
    max_risk_per_trade:  float = Field(0.5,  description="Max risk per trade as % of capital")
    cash_reserve_pct:    float = Field(30.0, description="Minimum cash reserve %")

    # ── Market session timings (IST 24h) ──────────────────────────
    session_open:          str = Field("09:15")
    session_close:         str = Field("15:30")
    opening_volatility_end:str = Field("10:30")
    midday_start:          str = Field("10:30")
    midday_end:            str = Field("14:00")
    power_hour_start:      str = Field("14:00")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# ── Token persistence (local file, like original bridge) ─────────
_TOKEN_FILE = Path.home() / ".fm_bridge_token.json"


def load_token() -> dict:
    if _TOKEN_FILE.exists():
        try:
            return json.loads(_TOKEN_FILE.read_text())
        except Exception:
            pass
    return {}


def save_token(data: dict) -> None:
    _TOKEN_FILE.write_text(json.dumps(data, indent=2))
    _TOKEN_FILE.chmod(0o600)


# ── Index constants ───────────────────────────────────────────────
# All 10 NSE indices tracked.  Token map from Kite instruments.
INSTRUMENT_MAP: dict[str, int] = {
    "NIFTY 50":          256265,
    "BANK NIFTY":        260105,
    "NIFTY IT":          5633,
    "NIFTY AUTO":        3,
    "NIFTY METAL":       11,
    "NIFTY PHARMA":      8,
    "NIFTY FMCG":        6,
    "NIFTY MIDCAP 100":  14,
    "NIFTY NEXT 50":     264969,
    "NIFTY FINANCIAL":   6548513,
}

EXCHANGE_MAP: dict[str, str] = {
    "NIFTY 50":          "NSE:NIFTY 50",
    "BANK NIFTY":        "NSE:NIFTY BANK",
    "NIFTY IT":          "NSE:NIFTY IT",
    "NIFTY AUTO":        "NSE:NIFTY AUTO",
    "NIFTY METAL":       "NSE:NIFTY METAL",
    "NIFTY PHARMA":      "NSE:NIFTY PHARMA",
    "NIFTY FMCG":        "NSE:NIFTY FMCG",
    "NIFTY MIDCAP 100":  "NSE:NIFTY MIDCAP 100",
    "NIFTY NEXT 50":     "NSE:NIFTY NEXT 50",
    "NIFTY FINANCIAL":   "NSE:NIFTY FIN SERVICE",
}

# NSE option chain symbol map
NSE_OC_SYMBOL_MAP: dict[str, str] = {
    "NIFTY 50":      "NIFTY",
    "BANK NIFTY":    "BANKNIFTY",
    "NIFTY IT":      "NIFTYIT",
    "NIFTY FINANCIAL":"FINNIFTY",
}

# Lot sizes per index
LOT_SIZES: dict[str, int] = {
    "NIFTY 50":        25,
    "BANK NIFTY":      15,
    "NIFTY IT":        25,
    "NIFTY AUTO":      25,
    "NIFTY METAL":     25,
    "NIFTY PHARMA":    25,
    "NIFTY FMCG":      25,
    "NIFTY MIDCAP 100":50,
    "NIFTY NEXT 50":   25,
    "NIFTY FINANCIAL": 25,
}

# Strike step per index
STRIKE_STEP: dict[str, int] = {
    "NIFTY 50":     50,
    "BANK NIFTY":  100,
    "NIFTY FINANCIAL": 50,
    "_default":     50,
}

# Market sessions
MARKET_SESSIONS = {
    "PRE_OPEN":           ("09:00", "09:15"),
    "OPENING_VOLATILITY": ("09:15", "10:30"),
    "MIDDAY_CHOP":        ("10:30", "14:00"),
    "POWER_HOUR":         ("14:00", "15:00"),
    "CLOSING":            ("15:00", "15:30"),
    "POST_CLOSE":         ("15:30", "23:59"),
}


# ── Singleton ─────────────────────────────────────────────────────
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings