"""
FM Trading Agency — SQLite Journal Store
==========================================
Async SQLite trade journal.
Stores every trade with full verdict attribution.
Starts local (SQLite file) → migrates to Supabase when hosted.

TradingAgents TradingMemoryLog pattern:
  Every decision → PENDING
  Every outcome → RESOLVED (WIN/LOSS/BREAKEVEN)
  Feedback loop closes after N trades.
"""

from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from db.models import TradeEntry, TradeStatus, TradeOutcome, CloseTradeRequest, VerdictType

log = logging.getLogger("fm.journal.store")

_DB_PATH = Path(__file__).parent.parent / "data" / "journal.db"


def _ensure_dir():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    _ensure_dir()
    c = sqlite3.connect(str(_DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db():
    """Create tables if they don't exist."""
    c = _conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS trades (
        id             TEXT PRIMARY KEY,
        created_at     TEXT NOT NULL,
        trade_date     TEXT NOT NULL,
        symbol         TEXT NOT NULL DEFAULT 'NIFTY 50',
        verdict        TEXT NOT NULL,
        regime         TEXT DEFAULT 'UNKNOWN',
        execution_score INTEGER DEFAULT 0,
        confidence     INTEGER DEFAULT 0,
        rationale      TEXT DEFAULT '',
        layer_scores   TEXT DEFAULT '{}',
        direction      TEXT DEFAULT 'LONG',
        instrument     TEXT DEFAULT '',
        entry_price    REAL,
        stop_loss      REAL,
        target1        REAL,
        target2        REAL,
        target3        REAL,
        rr_ratio       REAL,
        lot_size       INTEGER DEFAULT 25,
        units          INTEGER DEFAULT 1,
        holding_period TEXT DEFAULT 'INTRADAY',
        hedge_type     TEXT DEFAULT 'NONE',
        hedge_strike   REAL,
        hedge_premium  REAL,
        hedge_cost_pct REAL,
        status         TEXT DEFAULT 'PENDING',
        entry_time     TEXT,
        exit_time      TEXT,
        exit_price     REAL,
        exit_reason    TEXT DEFAULT '',
        gross_pnl      REAL,
        hedge_pnl      REAL,
        net_pnl        REAL,
        net_pnl_pct    REAL,
        outcome        TEXT DEFAULT 'PENDING',
        entry_session  TEXT DEFAULT '',
        entry_hour     INTEGER,
        vix_at_entry   REAL,
        spot_at_verdict REAL,
        notes          TEXT DEFAULT ''
    );

    CREATE INDEX IF NOT EXISTS idx_trades_date    ON trades(trade_date);
    CREATE INDEX IF NOT EXISTS idx_trades_status  ON trades(status);
    CREATE INDEX IF NOT EXISTS idx_trades_outcome ON trades(outcome);
    CREATE INDEX IF NOT EXISTS idx_trades_symbol  ON trades(symbol);

    CREATE TABLE IF NOT EXISTS capital_snapshots (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        snap_date  TEXT NOT NULL,
        capital    REAL NOT NULL,
        daily_pnl  REAL DEFAULT 0,
        weekly_pnl REAL DEFAULT 0,
        dd_pct     REAL DEFAULT 0,
        kill_switch INTEGER DEFAULT 0,
        notes      TEXT DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_cap_date ON capital_snapshots(snap_date);
    """)
    c.commit()
    c.close()
    log.info("Journal DB initialised at %s", _DB_PATH)


# ═══════════════════════════════════════════════════════════════
# TRADE CRUD
# ═══════════════════════════════════════════════════════════════

def log_trade(trade: TradeEntry) -> TradeEntry:
    """Insert a new trade entry."""
    c = _conn()
    c.execute("""
        INSERT INTO trades (
            id, created_at, trade_date, symbol, verdict, regime,
            execution_score, confidence, rationale, layer_scores,
            direction, instrument, entry_price, stop_loss,
            target1, target2, target3, rr_ratio, lot_size, units,
            holding_period, hedge_type, hedge_strike, hedge_premium,
            hedge_cost_pct, status, entry_time, entry_hour,
            entry_session, vix_at_entry, spot_at_verdict, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        trade.id, trade.created_at.isoformat(), trade.trade_date.isoformat(),
        trade.symbol, trade.verdict.value, trade.regime,
        trade.execution_score, trade.confidence, trade.rationale,
        json.dumps(trade.layer_scores),
        trade.direction, trade.instrument, trade.entry_price, trade.stop_loss,
        trade.target1, trade.target2, trade.target3, trade.rr_ratio,
        trade.lot_size, trade.units, trade.holding_period,
        trade.hedge_type, trade.hedge_strike, trade.hedge_premium,
        trade.hedge_cost_pct, trade.status.value, 
        trade.entry_time.isoformat() if trade.entry_time else None,
        trade.entry_hour, trade.entry_session,
        trade.vix_at_entry, trade.spot_at_verdict, trade.notes,
    ))
    c.commit()
    c.close()
    log.info("Trade logged: %s %s %s @ %s", trade.id, trade.verdict.value, trade.symbol, trade.entry_price)
    return trade


def close_trade(req: CloseTradeRequest, capital: float = 500_000) -> Optional[TradeEntry]:
    """Close a trade: set exit price, compute P&L, determine outcome."""
    c = _conn()
    row = c.execute("SELECT * FROM trades WHERE id = ?", (req.trade_id,)).fetchone()
    if not row:
        c.close()
        return None

    entry_price = row["entry_price"] or 0
    direction   = row["direction"]
    lot_size    = row["lot_size"] or 25
    units       = row["units"] or 1

    # Compute P&L
    if direction == "LONG":
        pts_pnl = req.exit_price - entry_price
    else:
        pts_pnl = entry_price - req.exit_price

    gross_pnl   = pts_pnl * lot_size * units
    hedge_pnl   = req.hedge_pnl
    net_pnl     = gross_pnl + hedge_pnl
    net_pnl_pct = (net_pnl / capital * 100) if capital > 0 else 0

    # Outcome
    if net_pnl > 0:
        outcome = TradeOutcome.WIN.value
    elif net_pnl < 0:
        outcome = TradeOutcome.LOSS.value
    else:
        outcome = TradeOutcome.BREAKEVEN.value

    now = datetime.utcnow().isoformat()

    c.execute("""
        UPDATE trades SET
            exit_price = ?, exit_time = ?, exit_reason = ?,
            gross_pnl = ?, hedge_pnl = ?, net_pnl = ?, net_pnl_pct = ?,
            outcome = ?, status = ?, notes = notes || ?
        WHERE id = ?
    """, (
        req.exit_price, now, req.exit_reason,
        round(gross_pnl, 2), round(hedge_pnl, 2), round(net_pnl, 2), round(net_pnl_pct, 4),
        outcome, TradeStatus.CLOSED.value,
        f"\n[Closed: {req.notes}]" if req.notes else "",
        req.trade_id,
    ))
    c.commit()

    updated = c.execute("SELECT * FROM trades WHERE id = ?", (req.trade_id,)).fetchone()
    c.close()

    trade = _row_to_trade(updated) if updated else None
    if trade:
        log.info("Trade closed: %s → %s PnL=₹%.0f", trade.id, outcome, net_pnl)
    return trade


def get_trade(trade_id: str) -> Optional[TradeEntry]:
    c = _conn()
    row = c.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
    c.close()
    return _row_to_trade(row) if row else None


def get_trades(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date:   Optional[str] = None,
    limit:     int = 100,
) -> list[TradeEntry]:
    """Query trades with optional filters."""
    c = _conn()
    q = "SELECT * FROM trades WHERE 1=1"
    params: list = []

    if status:
        q += " AND status = ?"; params.append(status)
    if symbol:
        q += " AND symbol = ?"; params.append(symbol)
    if from_date:
        q += " AND trade_date >= ?"; params.append(from_date)
    if to_date:
        q += " AND trade_date <= ?"; params.append(to_date)

    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = c.execute(q, params).fetchall()
    c.close()
    return [_row_to_trade(r) for r in rows]


def get_closed_trades(limit: int = 500) -> list[TradeEntry]:
    return get_trades(status="CLOSED", limit=limit)


# ═══════════════════════════════════════════════════════════════
# CAPITAL SNAPSHOTS
# ═══════════════════════════════════════════════════════════════

def log_capital_snapshot(
    capital: float, daily_pnl: float = 0, weekly_pnl: float = 0,
    dd_pct: float = 0, kill_switch: bool = False, notes: str = "",
):
    c = _conn()
    c.execute("""
        INSERT INTO capital_snapshots (snap_date, capital, daily_pnl, weekly_pnl, dd_pct, kill_switch, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date.today().isoformat(), capital, daily_pnl, weekly_pnl, dd_pct, int(kill_switch), notes))
    c.commit()
    c.close()


def get_capital_history(days: int = 90) -> list[dict]:
    c = _conn()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = c.execute(
        "SELECT * FROM capital_snapshots WHERE snap_date >= ? ORDER BY snap_date",
        (cutoff,)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _row_to_trade(row) -> TradeEntry:
    d = dict(row)
    d["layer_scores"] = json.loads(d.get("layer_scores") or "{}")
    d["created_at"]   = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.utcnow()
    d["trade_date"]   = date.fromisoformat(d["trade_date"]) if d.get("trade_date") else date.today()
    d["entry_time"]   = datetime.fromisoformat(d["entry_time"]) if d.get("entry_time") else None
    d["exit_time"]    = datetime.fromisoformat(d["exit_time"]) if d.get("exit_time") else None
    d["verdict"]      = VerdictType(d.get("verdict", "BULL_TRADE"))
    d["status"]       = TradeStatus(d.get("status", "PENDING"))
    d["outcome"]      = TradeOutcome(d.get("outcome", "PENDING"))
    return TradeEntry(**d)
