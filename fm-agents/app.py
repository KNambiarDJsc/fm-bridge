"""
FM Trading Agency — Agent Pipeline Server
==========================================
FastAPI server exposing:
  POST /api/analyze   — run full 9-layer pipeline, return FinalVerdict
  POST /api/chat      — copilot chat (Phase 4 — stub for now)
  GET  /health        — pipeline health check

Called by:
  • fm-web (Next.js frontend) — main analysis trigger
  • fm-alerts — morning briefing at 9:15 AM
  • Telegram bot (Phase 6)

Run:
  python app.py
  # or:
  uvicorn app:app --port 8003 --reload
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt = "%H:%M:%S",
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
log = logging.getLogger("fm.agents.app")


# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title       = "FM Trading Agency — Agent Pipeline",
    description = "9-layer AI analysis pipeline returning FinalVerdict",
    version     = "3.0.0",
    docs_url    = "/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)


# ── Lazy-loaded pipeline (built once on first request) ────────────
_pipeline = None
_llm_quick = None
_llm_deep  = None


def _get_pipeline():
    global _pipeline, _llm_quick, _llm_deep
    if _pipeline is None:
        log.info("Building pipeline ...")
        from llm.provider   import get_llm
        from pipeline.graph import build_pipeline
        _llm_quick = get_llm("quick")
        _llm_deep  = get_llm("deep")
        _pipeline  = build_pipeline(_llm_quick, _llm_deep)
        log.info("Pipeline ready ✓")
    return _pipeline


# ════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    symbol:      str   = "NIFTY 50"
    bridge_url:  str   = "http://localhost:8002"
    timeout:     int   = 15


class ChatRequest(BaseModel):
    question:    str
    symbol:      str   = "NIFTY 50"
    context:     Optional[dict] = None   # last FinalVerdict for context


# ════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    from config import get_settings
    s = get_settings()
    return {
        "status":    "ok",
        "service":   "fm-agents",
        "version":   "3.0.0",
        "provider":  s.llm_provider,
        "bridge":    s.bridge_url,
        "ts":        int(time.time() * 1000),
    }


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """
    Run the full 9-layer pipeline and return a FinalVerdict.

    Steps:
      1. Fetch data from bridge (fm-bridge)
      2. Run quant engine (fm-quant)
      3. Fetch news headlines
      4. Run event intelligence
      5. Execute LangGraph pipeline (L1-L6 parallel → L7-L9 sequential)
      6. Return FinalVerdict

    Typical latency: 8-15 seconds.
    """
    t0 = time.time()
    log.info("▶  Analysis requested: %s", req.symbol)

    try:
        # ── Step 1+2+3: Build context ─────────────────────────────
        from pipeline.context_builder import build_context
        state = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: build_context(
                symbol     = req.symbol,
                bridge_url = req.bridge_url,
                timeout    = req.timeout,
            )
        )

        # ── Step 4: Event intelligence ────────────────────────────
        try:
            from event.intelligence import analyse_events
            global _llm_quick
            if _llm_quick is None:
                from llm.provider import get_llm
                _llm_quick = get_llm("quick")
            event_ctx = analyse_events(
                headlines = state.get("news_headlines", []),
                llm       = _llm_quick,
            )
            state["event_context"] = event_ctx.to_dict()
        except Exception as e:
            log.warning("Event intelligence failed: %s", e)
            state["event_context"] = {}

        # ── Step 5: Run pipeline ──────────────────────────────────
        pipeline = _get_pipeline()
        result   = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: pipeline.invoke(state)
        )

        verdict = result.get("final_verdict", {})
        verdict["pipeline_ms"] = int((time.time() - t0) * 1000)

        log.info(
            "✓  %s → %s | score=%s | %.1fs",
            req.symbol,
            verdict.get("verdict", "?"),
            verdict.get("execution_score", "?"),
            time.time() - t0,
        )
        return {"status": "success", "data": verdict}

    except Exception as e:
        log.exception("Pipeline error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    AI Copilot Chat — answer questions about the current analysis.
    The chat is NOT the product — it is the intelligence access layer.

    Questions it handles:
      "Why bearish?" "What changed?" "Compare Nifty vs BankNifty."
      "Why hedge needed?" "Is this a good setup?"
    """
    try:
        global _llm_quick
        if _llm_quick is None:
            from llm.provider import get_llm
            _llm_quick = get_llm("quick")

        # Build context prompt from last verdict if available
        ctx_str = ""
        if req.context:
            ctx_str = (
                f"\nCurrent analysis context:\n"
                f"  Symbol: {req.context.get('best_index', req.symbol)}\n"
                f"  Verdict: {req.context.get('verdict', '?')}\n"
                f"  Regime: {req.context.get('regime', '?')}\n"
                f"  Score: {req.context.get('execution_score', '?')}/100\n"
                f"  Rationale: {req.context.get('rationale', '')}\n"
            )

        prompt = (
            f"You are FM Trading Agency Copilot — an AI assistant for Indian equity derivatives traders.\n"
            f"Answer the trader's question concisely (max 3-4 sentences).\n"
            f"Be specific: use numbers, not vague statements.\n"
            f"Focus on NSE indices, options, and risk management.\n"
            f"{ctx_str}\n"
            f"Trader asks: {req.question}"
        )

        response = _llm_quick.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)

        return {"status": "success", "answer": answer.strip()}

    except Exception as e:
        log.exception("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from config import get_settings
    s = get_settings()
    print(f"\n  FM Trading Agency — Agent Pipeline v3.0")
    print(f"  Provider: {s.llm_provider}")
    print(f"  Bridge:   {s.bridge_url}")
    print(f"  Port:     8003\n")

    uvicorn.run(
        "app:app",
        host       = "0.0.0.0",
        port       = 8003,
        log_level  = "warning",
        access_log = False,
        reload     = False,
    )