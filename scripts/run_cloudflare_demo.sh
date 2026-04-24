#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${ARSITRAD_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${ARSITRAD_BACKEND_PORT:-8000}"
FRONTEND_HOST="${ARSITRAD_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${ARSITRAD_FRONTEND_PORT:-3000}"
BACKEND_LOG="${ARSITRAD_BACKEND_LOG:-/tmp/arsitrad-api.log}"
FRONTEND_LOG="${ARSITRAD_FRONTEND_LOG:-/tmp/arsitrad-next.log}"
BACKEND_TUNNEL_LOG="${ARSITRAD_BACKEND_TUNNEL_LOG:-/tmp/arsitrad-api-cloudflared.log}"
FRONTEND_TUNNEL_LOG="${ARSITRAD_FRONTEND_TUNNEL_LOG:-/tmp/arsitrad-web-cloudflared.log}"

BACKEND_PID=""
FRONTEND_PID=""
BACKEND_TUNNEL_PID=""
FRONTEND_TUNNEL_PID=""

cleanup() {
  for pid in "${FRONTEND_TUNNEL_PID}" "${BACKEND_TUNNEL_PID}" "${FRONTEND_PID}" "${BACKEND_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

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

wait_for_tunnel_url() {
  local log_path="$1"
  local name="$2"
  python - "$log_path" "$name" <<'PY'
import re, sys, time
log_path, name = sys.argv[1], sys.argv[2]
pattern = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")
for _ in range(120):
    try:
        text = open(log_path, "r", encoding="utf-8", errors="ignore").read()
    except FileNotFoundError:
        text = ""
    match = pattern.search(text)
    if match:
        print(match.group(0))
        raise SystemExit(0)
    time.sleep(1)
print(f"Could not detect {name} tunnel URL in {log_path}", file=sys.stderr)
raise SystemExit(1)
PY
}

require_cmd cloudflared
require_cmd npm

cd "${ROOT_DIR}"

if [[ ! -d "web/node_modules" ]]; then
  echo "web/node_modules missing; run: cd web && npm install" >&2
  exit 1
fi

cat <<'EOF'
WARNING: this creates public trycloudflare.com URLs for the Arsitrad demo.
Do not run it if the local backend should not be reachable from the internet.
EOF

: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"
: > "${BACKEND_TUNNEL_LOG}"
: > "${FRONTEND_TUNNEL_LOG}"

echo "Starting backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
python -m uvicorn api.server:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
wait_for_url "http://${BACKEND_HOST}:${BACKEND_PORT}/health" "backend"

echo "Opening backend Cloudflare tunnel"
cloudflared tunnel --url "http://${BACKEND_HOST}:${BACKEND_PORT}" >"${BACKEND_TUNNEL_LOG}" 2>&1 &
BACKEND_TUNNEL_PID=$!
API_TUNNEL_URL="$(wait_for_tunnel_url "${BACKEND_TUNNEL_LOG}" "backend")"
echo "Backend tunnel: ${API_TUNNEL_URL}"

echo "Starting frontend on http://${FRONTEND_HOST}:${FRONTEND_PORT} with backend ${API_TUNNEL_URL}"
(
  cd "${ROOT_DIR}/web"
  NEXT_PUBLIC_API_BASE_URL="${API_TUNNEL_URL}" npm run dev -- --hostname "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
) >"${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
wait_for_url "http://${FRONTEND_HOST}:${FRONTEND_PORT}" "frontend"

echo "Opening frontend Cloudflare tunnel"
cloudflared tunnel --url "http://${FRONTEND_HOST}:${FRONTEND_PORT}" >"${FRONTEND_TUNNEL_LOG}" 2>&1 &
FRONTEND_TUNNEL_PID=$!
FRONTEND_TUNNEL_URL="$(wait_for_tunnel_url "${FRONTEND_TUNNEL_LOG}" "frontend")"

cat <<EOF

Arsitrad public demo is running.
Frontend URL: ${FRONTEND_TUNNEL_URL}
Backend URL:  ${API_TUNNEL_URL}

CORS note: api/server.py allows https://*.trycloudflare.com by default.
If you disable the default regex, set:
ARSITRAD_WEB_ALLOWED_ORIGINS=${FRONTEND_TUNNEL_URL}

Logs:
Backend:         ${BACKEND_LOG}
Frontend:        ${FRONTEND_LOG}
Backend tunnel:  ${BACKEND_TUNNEL_LOG}
Frontend tunnel: ${FRONTEND_TUNNEL_LOG}

Press Ctrl+C to stop backend, frontend, and both tunnels.
EOF

wait
