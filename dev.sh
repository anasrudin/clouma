#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$ROOT/apps/api"
WEB_DIR="$ROOT/apps/web"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[clouma]${RESET} $*"; }
ok()   { echo -e "${GREEN}[clouma]${RESET} $*"; }
warn() { echo -e "${YELLOW}[clouma]${RESET} $*"; }
die()  { echo -e "${RED}[clouma]${RESET} $*" >&2; exit 1; }

cleanup() {
  warn "Shutting down..."
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}

# ── preflight ────────────────────────────────────────────────────────────────

[[ -f "$ROOT/.env" ]] || die ".env not found — copy .env.example and fill in your values"

command -v docker  >/dev/null 2>&1 || die "docker not found"
command -v python3 >/dev/null 2>&1 || die "python3 not found"
command -v node    >/dev/null 2>&1 || die "node not found"

# ── claw orchestrator ─────────────────────────────────────────────────────────

CLAW_BIN="$ROOT/bin/claw"
if [[ -f "$CLAW_BIN" ]]; then
  export CLAW_BINARY="$CLAW_BIN"
  ok "claw orchestrator ready at bin/claw"
else
  warn "bin/claw not found — agent execution will fail. Add ANTHROPIC_API_KEY to .env and ensure bin/claw exists."
fi

# ── infrastructure ───────────────────────────────────────────────────────────

log "Starting postgres + redis..."
docker compose -f "$ROOT/docker-compose.yml" up -d postgres redis

log "Waiting for postgres to be healthy..."
until docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
    pg_isready -U clouma -d clouma >/dev/null 2>&1; do
  sleep 1
done
ok "Postgres ready"

# ── migrations ───────────────────────────────────────────────────────────────

log "Running migrations..."
(
  cd "$API_DIR"
  if [[ -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi
  set -a; source "$ROOT/.env"; set +a
  alembic upgrade head
)
ok "Migrations done"

# ── api ──────────────────────────────────────────────────────────────────────

log "Starting API on :8000..."
(
  cd "$API_DIR/.."
  if [[ -f "$API_DIR/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$API_DIR/.venv/bin/activate"
  fi
  set -a; source "$ROOT/.env"; set +a
  PYTHONPATH="$API_DIR${PYTHONPATH:+:$PYTHONPATH}" uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | sed "s/^/${CYAN}[api]${RESET} /"
) &
API_PID=$!

# ── web ──────────────────────────────────────────────────────────────────────

log "Starting web on :3000..."
(
  cd "$WEB_DIR"
  # install deps if node_modules missing
  [[ -d node_modules ]] || npm install --silent
  npm run dev 2>&1 | sed "s/^/${GREEN}[web]${RESET} /"
) &
WEB_PID=$!

trap cleanup INT TERM EXIT

ok "All services up — API: http://localhost:8000  |  Web: http://localhost:3000"
log "Press Ctrl+C to stop"

wait "$API_PID" "$WEB_PID"
