"""
FM Trading Agency — Journal & Analytics Server
=================================================
FastAPI service for Phase 5: Performance Intelligence.

Endpoints:
  POST /api/trades              — log a new trade
  POST /api/trades/close        — close a trade with exit price
  GET  /api/trades              — list trades (filters: status, symbol, dates)
  GET  /api/trades/{id}         — get single trade
  GET  /api/analytics/dashboard — full analytics dashboard
  GET  /api/analytics/weekly    — weekly P&L vs 2% target
  GET  /api/analytics/agents    — agent accuracy scorecard
  GET  /api/analytics/time      — time-of-day analysis
  GET  /api/analytics/drawdown  — drawdown events
  GET  /api/analytics/hedge     — hedge effectiveness
  GET  /api/analytics/streaks   — streak analysis
  POST /api/backtest/run        — run signal backtest on historical data
  POST /api/backtest/walk-forward — walk-forward validation
  GET  /health                  — health check

Run:
  python app.py
  # or:
  uvicorn app:app --port 8004 --reload
"""

from __future__ import annotations

import logging
from typing import Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db.store import init_db, log_trade, close_trade, get_trade, get_trades
from db.models import TradeEntry, CloseTradeRequest
from analytics.engine import (
    compute_full_dashboard, compute_weekly_summaries,
    compute_agent_accuracy, compute_time_of_day,
    compute_drawdowns, compute_hedge_effectiveness,
    compute_verdict_breakdown, compute_streaks,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fm.journal.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("Journal DB ready")
    yield

app = FastAPI(
    title       = "FM Trading Agency — Journal & Analytics",
    description = "Trade journal, performance analytics, backtesting",
    version     = "5.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# TRADE ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post("/api/trades")
def api_log_trade(trade: TradeEntry):
    result = log_trade(trade)
    return {"status": "ok", "trade": result.model_dump(mode="json")}


@app.post("/api/trades/close")
def api_close_trade(req: CloseTradeRequest):
    capital = 500_000  # TODO: read from capital shield
    result = close_trade(req, capital=capital)
    if not result:
        raise HTTPException(404, f"Trade {req.trade_id} not found")
    return {"status": "ok", "trade": result.model_dump(mode="json")}


@app.get("/api/trades")
def api_list_trades(
    status:    Optional[str] = Query(None),
    symbol:    Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date:   Optional[str] = Query(None),
    limit:     int           = Query(100, ge=1, le=1000),
):
    trades = get_trades(status=status, symbol=symbol, from_date=from_date, to_date=to_date, limit=limit)
    return {"trades": [t.model_dump(mode="json") for t in trades], "count": len(trades)}


@app.get("/api/trades/{trade_id}")
def api_get_trade(trade_id: str):
    t = get_trade(trade_id)
    if not t:
        raise HTTPException(404, f"Trade {trade_id} not found")
    return {"trade": t.model_dump(mode="json")}


# ═══════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/analytics/dashboard")
def api_dashboard(capital: float = Query(500_000)):
    return compute_full_dashboard(capital)


@app.get("/api/analytics/weekly")
def api_weekly(capital: float = Query(500_000)):
    ws = compute_weekly_summaries(capital=capital)
    return {"weeks": [w.model_dump() for w in ws]}


@app.get("/api/analytics/agents")
def api_agents():
    agents = compute_agent_accuracy()
    return {"agents": [a.model_dump() for a in agents]}


@app.get("/api/analytics/time")
def api_time_of_day():
    tod = compute_time_of_day()
    return {"hours": [h.model_dump() for h in tod]}


@app.get("/api/analytics/drawdown")
def api_drawdown(capital: float = Query(500_000)):
    dd = compute_drawdowns(capital=capital)
    return {"drawdowns": [d.model_dump() for d in dd]}


@app.get("/api/analytics/hedge")
def api_hedge():
    h = compute_hedge_effectiveness()
    return h.model_dump()


@app.get("/api/analytics/streaks")
def api_streaks():
    return compute_streaks()


@app.get("/api/analytics/verdicts")
def api_verdicts():
    return compute_verdict_breakdown()


# ═══════════════════════════════════════════════════════════════
# BACKTEST ENDPOINTS
# ═══════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    symbol:     str   = "NIFTY 50"
    strategy:   str   = "RSI_50_70"    # or "ALL"
    bridge_url: str   = "http://localhost:8002"
    interval:   str   = "day"
    range_days: int   = 365


@app.post("/api/backtest/run")
def api_backtest(req: BacktestRequest):
    import requests
    import pandas as pd
    from backtest.signals import run_all_strategies, run_backtest, SIGNAL_STRATEGIES

    # Fetch historical from bridge
    try:
        r = requests.get(
            f"{req.bridge_url}/historical",
            params={"symbol": req.symbol, "interval": req.interval, "range": f"{req.range_days}d"},
            timeout=15,
        )
        data = r.json()
        bars = data.get("data", [])
        if not bars:
            raise HTTPException(400, "No historical data from bridge")
    except requests.RequestException as e:
        raise HTTPException(502, f"Bridge error: {e}")

    df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
    df["close"] = df["close"].astype(float)

    if req.strategy == "ALL":
        results = run_all_strategies(df, symbol=req.symbol)
        return {"results": [r.to_dict() for r in results]}
    elif req.strategy in SIGNAL_STRATEGIES:
        entries, exits = SIGNAL_STRATEGIES[req.strategy](df)
        result = run_backtest(df, entries, exits, strategy_name=req.strategy, symbol=req.symbol)
        return {"result": result.to_dict()}
    else:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}. Available: {list(SIGNAL_STRATEGIES.keys())}")


class WalkForwardRequest(BaseModel):
    symbol:     str   = "NIFTY 50"
    strategy:   str   = "EMA_9_20"
    bridge_url: str   = "http://localhost:8002"
    train_pct:  float = 0.7


@app.post("/api/backtest/walk-forward")
def api_walk_forward(req: WalkForwardRequest):
    import requests
    import pandas as pd
    from backtest.signals import walk_forward, SIGNAL_STRATEGIES

    if req.strategy not in SIGNAL_STRATEGIES:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")

    try:
        r = requests.get(
            f"{req.bridge_url}/historical",
            params={"symbol": req.symbol, "interval": "day", "range": "365d"},
            timeout=15,
        )
        bars = r.json().get("data", [])
        if not bars:
            raise HTTPException(400, "No data")
    except requests.RequestException as e:
        raise HTTPException(502, f"Bridge error: {e}")

    df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
    df["close"] = df["close"].astype(float)

    result = walk_forward(
        df, SIGNAL_STRATEGIES[req.strategy],
        train_pct=req.train_pct, symbol=req.symbol, strategy_name=req.strategy,
    )
    return result


# ═══════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    import time
    return {"status": "ok", "service": "fm-journal", "version": "5.0.0", "ts": int(time.time() * 1000)}


if __name__ == "__main__":
    print("\n  FM Trading Agency — Journal & Analytics v5.0")
    print("  Port: 8004\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8004, log_level="warning", reload=False)
