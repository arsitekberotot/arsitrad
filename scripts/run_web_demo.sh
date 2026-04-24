#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${ARSITRAD_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${ARSITRAD_BACKEND_PORT:-8000}"
FRONTEND_HOST="${ARSITRAD_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${ARSITRAD_FRONTEND_PORT:-3000}"
API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"
SMOKE_ONLY=0

if [[ "${1:-}" == "--smoke-only" ]]; then
  SMOKE_ONLY=1
fi

BACKEND_LOG="${ARSITRAD_BACKEND_LOG:-/tmp/arsitrad-api.log}"
FRONTEND_LOG="${ARSITRAD_FRONTEND_LOG:-/tmp/arsitrad-next.log}"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

wait_for_url() {
  local url="$1"
  local name="$2"
  python - "$url" "$name" <<'PY'
import sys, time, urllib.request
url, name = sys.argv[1], sys.argv[2]
last = None
for _ in range(90):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if 200 <= response.status < 500:
                print(f"{name} ready: {url}")
                raise SystemExit(0)
    except Exception as exc:
        last = exc
        time.sleep(1)
print(f"{name} did not become ready at {url}: {last}", file=sys.stderr)
raise SystemExit(1)
PY
}

cd "${ROOT_DIR}"

if [[ ! -d "web/node_modules" ]]; then
  echo "web/node_modules missing; run: cd web && npm install" >&2
  exit 1
fi

: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"

echo "Starting Arsitrad FastAPI backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
python -m uvicorn api.server:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
wait_for_url "http://${BACKEND_HOST}:${BACKEND_PORT}/health" "backend"
wait_for_url "http://${BACKEND_HOST}:${BACKEND_PORT}/api/bootstrap" "bootstrap"

echo "Starting Arsitrad Next.js frontend on http://${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd "${ROOT_DIR}/web"
  NEXT_PUBLIC_API_BASE_URL="${API_BASE_URL}" npm run dev -- --hostname "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
) >"${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
wait_for_url "http://${FRONTEND_HOST}:${FRONTEND_PORT}" "frontend"

cat <<EOF

Arsitrad web demo is running.
Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}
API:      ${API_BASE_URL}

Logs:
Backend:  ${BACKEND_LOG}
Frontend: ${FRONTEND_LOG}

Press Ctrl+C to stop both processes.
EOF

if [[ "${SMOKE_ONLY}" == "1" ]]; then
  echo "Smoke-only mode complete; stopping processes."
  exit 0
fi

wait
