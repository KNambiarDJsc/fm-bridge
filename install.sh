#!/usr/bin/env bash
###############################################################################
# FM Trading Agency v5.0 — install.sh
#
# One-command setup for local development (no Docker required).
# Creates Python venvs, installs deps, copies env files.
#
# Usage:
#   chmod +x install.sh && ./install.sh
#
# After install:
#   ./run.sh              # start all services in tmux (or 5 terminals)
#   # or start individually:
#   source fm-bridge/venv/bin/activate && cd fm-bridge && python app.py
###############################################################################

set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

echo ""
echo "  FM Trading Agency v5.0 — Setup"
echo "  ================================"
echo ""

# ── Check Python & Node ────────────────────────────────────────
command -v python3 >/dev/null || error "Python 3.10+ required"
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PY_VER"

command -v node >/dev/null || error "Node.js 18+ required"
NODE_VER=$(node --version)
info "Node $NODE_VER"

# ── Python services ────────────────────────────────────────────
SERVICES=("fm-bridge" "fm-agents" "fm-journal" "fm-alerts")

for svc in "${SERVICES[@]}"; do
  echo ""
  info "Installing $svc..."
  cd "$svc"

  # Create venv if it doesn't exist
  if [ ! -d "venv" ]; then
    python3 -m venv venv
  fi

  # Install requirements
  ./venv/bin/pip install --upgrade pip -q
  ./venv/bin/pip install -r requirements.txt -q
  success "$svc installed"

  # Copy .env if it doesn't exist
  if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    warn "$svc/.env created from .env.example — fill in your credentials"
  fi

  cd ..
done

# ── fm-quant (no server — just needs to be importable by fm-agents) ─
echo ""
info "Installing fm-quant..."
cd fm-quant
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
./venv/bin/pip install -r requirements.txt -q 2>/dev/null || true
success "fm-quant installed"
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi
cd ..

# ── fm-web (Next.js) ───────────────────────────────────────────
echo ""
info "Installing fm-web..."
cd fm-web
npm install --silent
success "fm-web installed"
if [ ! -f ".env.local" ] && [ -f ".env.local.example" ]; then
  cp .env.local.example .env.local
  warn "fm-web/.env.local created — no changes needed for local dev"
fi
cd ..

# ── Summary ────────────────────────────────────────────────────
echo ""
echo "  ✅  All services installed."
echo ""
echo "  📋  Next steps:"
echo "  1. Fill in your credentials:"
echo "     fm-bridge/.env    → ZERODHA_USER_ID, ZERODHA_API_KEY, ZERODHA_PASSWORD, ZERODHA_TOTP_SECRET"
echo "     fm-agents/.env    → GOOGLE_API_KEY (or ANTHROPIC_API_KEY)"
echo "     fm-alerts/.env    → TELEGRAM_TOKEN, TELEGRAM_CHAT_ID"
echo ""
echo "  2. Start all services:"
echo "     ./run.sh"
echo ""
echo "  3. Open the dashboard:"
echo "     http://localhost:3000"
echo ""
