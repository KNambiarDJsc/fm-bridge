set -euo pipefail

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
echo "  FM Trading Agency v5.0 — Unified Setup"
echo "  ======================================="
echo ""

# ─────────────────────────────────────────────────────────────
# CHECK PYTHON
# ─────────────────────────────────────────────────────────────

command -v python >/dev/null 2>&1 || error "Python required"
PY_VER=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

info "Python $PY_VER detected"

# ─────────────────────────────────────────────────────────────
# CHECK NODE
# ─────────────────────────────────────────────────────────────

command -v node >/dev/null 2>&1 || error "Node.js required"
NODE_VER=$(node --version)

info "Node $NODE_VER detected"

# ─────────────────────────────────────────────────────────────
# CREATE ROOT VENV
# ─────────────────────────────────────────────────────────────

cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  info "Creating root virtual environment..."
  python -m venv .venv
  success "Root venv created"
else
  warn ".venv already exists"
fi

# ─────────────────────────────────────────────────────────────
# ACTIVATE VENV
# ─────────────────────────────────────────────────────────────

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source .venv/Scripts/activate
else
  source .venv/bin/activate
fi

# ─────────────────────────────────────────────────────────────
# UPGRADE PIP
# ─────────────────────────────────────────────────────────────

info "Upgrading pip..."
python -m pip install --upgrade pip wheel setuptools

# ─────────────────────────────────────────────────────────────
# INSTALL PYTHON REQUIREMENTS
# ─────────────────────────────────────────────────────────────

if [ ! -f "requirements.txt" ]; then
  error "requirements.txt not found"
fi

info "Installing Python dependencies..."
pip install -r requirements.txt

success "Python dependencies installed"

# ─────────────────────────────────────────────────────────────
# INSTALL WEB DEPENDENCIES
# ─────────────────────────────────────────────────────────────

if [ -d "fm-web" ]; then
  info "Installing fm-web dependencies..."

  cd fm-web
  npm install
  cd ..

  success "fm-web installed"
else
  warn "fm-web directory not found"
fi

# ─────────────────────────────────────────────────────────────
# CREATE ENV FILES
# ─────────────────────────────────────────────────────────────

SERVICES=("fm-bridge" "fm-agents" "fm-alerts" "fm-journal")

for svc in "${SERVICES[@]}"; do

  if [ -d "$svc" ]; then

    if [ ! -f "$svc/.env" ] && [ -f "$svc/.env.example" ]; then
      cp "$svc/.env.example" "$svc/.env"
      warn "$svc/.env created from .env.example"
    fi

  fi

done

# ─────────────────────────────────────────────────────────────
# WEB ENV
# ─────────────────────────────────────────────────────────────

if [ -d "fm-web" ]; then

  if [ ! -f "fm-web/.env.local" ] && [ -f "fm-web/.env.local.example" ]; then
    cp "fm-web/.env.local.example" "fm-web/.env.local"
    warn "fm-web/.env.local created"
  fi

fi

# ─────────────────────────────────────────────────────────────
# FINAL OUTPUT
# ─────────────────────────────────────────────────────────────

echo ""
echo "  ✅ FM Trading Agency Installed Successfully"
echo ""
echo "  Next Steps:"
echo ""
echo "  1. Fill credentials:"
echo ""
echo "     fm-bridge/.env"
echo "       - ZERODHA_USER_ID"
echo "       - ZERODHA_API_KEY"
echo "       - ZERODHA_PASSWORD"
echo "       - ZERODHA_TOTP_SECRET"
echo ""
echo "     fm-agents/.env"
echo "       - GOOGLE_API_KEY"
echo ""
echo "     fm-alerts/.env"
echo "       - TELEGRAM_TOKEN"
echo "       - TELEGRAM_CHAT_ID"
echo ""
echo "  2. Start system:"
echo ""
echo "     bash run.sh"
echo ""
echo "  3. Open dashboard:"
echo ""
echo "     http://localhost:3000"
echo ""
