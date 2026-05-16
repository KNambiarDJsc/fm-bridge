set -euo pipefail

SESSION="fm-trading"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  FM Trading Agency v5.0 — Runtime"
echo "  ================================="
echo ""

# ─────────────────────────────────────────────────────────────
# CHECK ROOT VENV
# ─────────────────────────────────────────────────────────────

if [ ! -d "$ROOT_DIR/.venv" ]; then
  error ".venv not found. Run ./install.sh first."
fi

# ─────────────────────────────────────────────────────────────
# CHECK NODE MODULES
# ─────────────────────────────────────────────────────────────

if [ ! -d "$ROOT_DIR/fm-web/node_modules" ]; then
  warn "fm-web/node_modules missing. Running npm install..."
  cd "$ROOT_DIR/fm-web"
  npm install
  cd "$ROOT_DIR"
fi

# ─────────────────────────────────────────────────────────────
# TMUX MODE
# ─────────────────────────────────────────────────────────────

if command -v tmux >/dev/null 2>&1; then

  # Kill old session if exists
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    warn "Existing tmux session found. Killing..."
    tmux kill-session -t "$SESSION"
  fi

  info "Starting services in tmux session: $SESSION"

  # Create session
  tmux new-session -d -s "$SESSION"

  # ── fm-bridge ────────────────────────────────────────────
  tmux rename-window -t "$SESSION:0" "bridge"
  tmux send-keys -t "$SESSION:0" "
    cd '$ROOT_DIR' &&
    source .venv/bin/activate &&
    cd fm-bridge &&
    python app.py
  " C-m

  # ── fm-agents ────────────────────────────────────────────
  tmux new-window -t "$SESSION" -n "agents"
  tmux send-keys -t "$SESSION:1" "
    cd '$ROOT_DIR' &&
    source .venv/bin/activate &&
    cd fm-agents &&
    python app.py
  " C-m

  # ── fm-journal ───────────────────────────────────────────
  tmux new-window -t "$SESSION" -n "journal"
  tmux send-keys -t "$SESSION:2" "
    cd '$ROOT_DIR' &&
    source .venv/bin/activate &&
    cd fm-journal &&
    python app.py
  " C-m

  # ── fm-alerts ────────────────────────────────────────────
  tmux new-window -t "$SESSION" -n "alerts"
  tmux send-keys -t "$SESSION:3" "
    cd '$ROOT_DIR' &&
    source .venv/bin/activate &&
    cd fm-alerts &&
    python app.py
  " C-m

  # ── fm-web ───────────────────────────────────────────────
  tmux new-window -t "$SESSION" -n "web"
  tmux send-keys -t "$SESSION:4" "
    cd '$ROOT_DIR/fm-web' &&
    npm run dev
  " C-m

  echo ""
  success "All services started."
  echo ""
  echo "  Dashboard:"
  echo "    http://localhost:3000"
  echo ""
  echo "  Attach to logs:"
  echo "    tmux attach -t $SESSION"
  echo ""
  echo "  Stop all:"
  echo "    tmux kill-session -t $SESSION"
  echo ""

else

  # ─────────────────────────────────────────────────────────
  # FALLBACK MODE (NO TMUX)
  # ─────────────────────────────────────────────────────────

  warn "tmux not installed."
  echo ""
  echo "Run these commands manually in separate terminals:"
  echo ""

  echo "1) fm-bridge"
  echo "----------------------------------------"
  echo "cd '$ROOT_DIR'"
  echo "source .venv/bin/activate"
  echo "cd fm-bridge && python app.py"
  echo ""

  echo "2) fm-agents"
  echo "----------------------------------------"
  echo "cd '$ROOT_DIR'"
  echo "source .venv/bin/activate"
  echo "cd fm-agents && python app.py"
  echo ""

  echo "3) fm-journal"
  echo "----------------------------------------"
  echo "cd '$ROOT_DIR'"
  echo "source .venv/bin/activate"
  echo "cd fm-journal && python app.py"
  echo ""

  echo "4) fm-alerts"
  echo "----------------------------------------"
  echo "cd '$ROOT_DIR'"
  echo "source .venv/bin/activate"
  echo "cd fm-alerts && python app.py"
  echo ""

  echo "5) fm-web"
  echo "----------------------------------------"
  echo "cd '$ROOT_DIR/fm-web'"
  echo "npm run dev"
  echo ""

fi