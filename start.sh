#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# InvestiGate — one-command startup script
#
# Usage:
#   ./start.sh            # normal start
#   ./start.sh --fresh    # reinstall all deps, then start
#   ./start.sh --help     # show this message
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; }
header()  { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }

# ── Args ──────────────────────────────────────────────────────────────────────
FRESH=false
for arg in "$@"; do
  case "$arg" in
    --fresh)  FRESH=true ;;
    --help|-h)
      echo "Usage: ./start.sh [--fresh] [--help]"
      echo "  --fresh   Wipe and reinstall Python venv + node_modules"
      exit 0 ;;
    *) error "Unknown argument: $arg"; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

echo ""
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║        InvestiGate Startup           ║${NC}"
echo -e "${BOLD}${BLUE}║   Multi-Agent Investment Analysis    ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: .env setup ────────────────────────────────────────────────────────
header "1/5  Environment"

ENV_FILE="$BACKEND_DIR/.env"
EXAMPLE_FILE="$SCRIPT_DIR/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ ! -f "$EXAMPLE_FILE" ]]; then
    error ".env.example not found at $EXAMPLE_FILE"
    exit 1
  fi
  cp "$EXAMPLE_FILE" "$ENV_FILE"
  success "Created backend/.env from .env.example (using Ollama defaults)"
else
  info "backend/.env already exists — skipping copy"
fi

# Read the active provider from the env file
LLM_PROVIDER=$(grep -E '^LLM_PROVIDER=' "$ENV_FILE" | cut -d= -f2 | tr -d ' ' || echo "ollama")
info "LLM_PROVIDER = ${BOLD}${LLM_PROVIDER}${NC}"

# ── Step 2: Ollama check (only if provider=ollama) ────────────────────────────
header "2/5  Ollama"

if [[ "$LLM_PROVIDER" == "ollama" ]]; then
  OLLAMA_URL=$(grep -E '^OLLAMA_BASE_URL=' "$ENV_FILE" | cut -d= -f2 | tr -d ' ' || echo "http://localhost:11434")
  ANALYST_MODEL=$(grep -E '^ANALYST_MODEL=' "$ENV_FILE" | cut -d= -f2 | tr -d ' ' || echo "llama3.1")
  EMBED_MODEL=$(grep -E '^EMBEDDING_MODEL=' "$ENV_FILE" | cut -d= -f2 | tr -d ' ' || echo "nomic-embed-text")

  if ! curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    warn "Ollama is not running at ${OLLAMA_URL}"
    echo ""
    echo "  Start Ollama in another terminal:  ${BOLD}ollama serve${NC}"
    echo "  Then pull the required models:"
    echo "    ${BOLD}ollama pull ${ANALYST_MODEL}${NC}"
    echo "    ${BOLD}ollama pull ${EMBED_MODEL}${NC}"
    echo ""
    read -r -p "  Ollama not detected. Continue anyway? [y/N] " REPLY
    [[ "$REPLY" =~ ^[Yy]$ ]] || exit 1
  else
    success "Ollama is running at ${OLLAMA_URL}"

    # Check if required models are available
    TAGS=$(curl -sf "${OLLAMA_URL}/api/tags" 2>/dev/null || echo '{"models":[]}')
    for MODEL in "$ANALYST_MODEL" "$EMBED_MODEL"; do
      if echo "$TAGS" | python3 -c "import sys,json; models=[m['name'] for m in json.load(sys.stdin).get('models',[])]; print('ok' if any('$MODEL' in m for m in models) else 'missing')" 2>/dev/null | grep -q "ok"; then
        success "Model ${BOLD}${MODEL}${NC} is available"
      else
        warn "Model ${BOLD}${MODEL}${NC} not found — pulling now..."
        ollama pull "$MODEL" || warn "Could not pull $MODEL — analysis may fail"
      fi
    done
  fi
else
  info "Provider is ${LLM_PROVIDER} — skipping Ollama check"
fi

# ── Step 3: Python venv + dependencies ───────────────────────────────────────
header "3/5  Python dependencies"

if [[ "$FRESH" == true && -d "$VENV_DIR" ]]; then
  info "Removing existing venv (--fresh)"
  rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  info "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
  success "Venv created at backend/.venv"
fi

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

info "Installing Python packages..."
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r "$BACKEND_DIR/requirements.txt"
success "Python packages ready"

# ── Step 4: Node dependencies ─────────────────────────────────────────────────
header "4/5  Node dependencies"

if [[ "$FRESH" == true && -d "$SCRIPT_DIR/node_modules" ]]; then
  info "Removing node_modules (--fresh)"
  rm -rf "$SCRIPT_DIR/node_modules"
fi

if [[ ! -d "$SCRIPT_DIR/node_modules" ]]; then
  info "Installing npm packages..."
  npm install --prefix "$SCRIPT_DIR" --silent
  success "npm packages installed"
else
  success "node_modules already present"
fi

# ── Step 5: Launch both servers ───────────────────────────────────────────────
header "5/5  Starting servers"

# Trap Ctrl+C to kill both child processes cleanly
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  echo ""
  info "Shutting down..."
  [[ -n "$BACKEND_PID" ]]  && kill "$BACKEND_PID"  2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  info "All servers stopped."
}
trap cleanup EXIT INT TERM

# Backend
info "Starting backend  →  http://localhost:8000"
"$VENV_DIR/bin/uvicorn" server:app \
  --host 0.0.0.0 --port 8000 --reload \
  --app-dir "$BACKEND_DIR" \
  2>&1 | sed "s/^/$(echo -e "${BLUE}[backend]${NC} ")/" &
BACKEND_PID=$!

# Give the backend a moment to bind before we print the ready banner
sleep 2

# Frontend
info "Starting frontend →  http://localhost:8080"
npm run dev --prefix "$SCRIPT_DIR" \
  2>&1 | sed "s/^/$(echo -e "${GREEN}[frontend]${NC}")/" &
FRONTEND_PID=$!

echo ""
echo -e "${BOLD}${GREEN}✓ InvestiGate is starting up!${NC}"
echo ""
echo -e "  Frontend  →  ${BOLD}http://localhost:8080${NC}"
echo -e "  Backend   →  ${BOLD}http://localhost:8000${NC}"
echo -e "  API docs  →  ${BOLD}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop all servers."
echo ""

# Wait for either process to exit
wait "$BACKEND_PID" "$FRONTEND_PID"
