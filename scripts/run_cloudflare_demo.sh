#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${ARSITRAD_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${ARSITRAD_BACKEND_PORT:-8000}"
FRONTEND_HOST="${ARSITRAD_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${ARSITRAD_FRONTEND_PORT:-3000}"
VISION_AUTOSTART="${ARSITRAD_VISION_AUTOSTART:-1}"
VISION_HOST="${ARSITRAD_VISION_HOST:-127.0.0.1}"
VISION_PORT="${ARSITRAD_VISION_PORT:-8080}"
VISION_BASE_URL="${ARSITRAD_VISION_BASE_URL:-http://${VISION_HOST}:${VISION_PORT}}"
VISION_MODEL_PATH="${ARSITRAD_VISION_MODEL_PATH:-}"
VISION_MMPROJ_PATH="${ARSITRAD_VISION_MMPROJ_PATH:-}"
VISION_LOG="${ARSITRAD_VISION_LOG:-/tmp/arsitrad-vision.log}"
VISION_PID=""
BACKEND_LOG="${ARSITRAD_BACKEND_LOG:-/tmp/arsitrad-api.log}"
FRONTEND_LOG="${ARSITRAD_FRONTEND_LOG:-/tmp/arsitrad-next.log}"
LLAMA_SERVER_BIN="${ARSITRAD_LLAMA_SERVER_BIN:-llama-server}"
REQUIRE_VISION="${ARSITRAD_REQUIRE_VISION:-0}"
BACKEND_TUNNEL_LOG="${ARSITRAD_BACKEND_TUNNEL_LOG:-/tmp/arsitrad-api-cloudflared.log}"
FRONTEND_TUNNEL_LOG="${ARSITRAD_FRONTEND_TUNNEL_LOG:-/tmp/arsitrad-web-cloudflared.log}"

BACKEND_PID=""
FRONTEND_PID=""
BACKEND_TUNNEL_PID=""
FRONTEND_TUNNEL_PID=""

cleanup() {
  for pid in "${FRONTEND_TUNNEL_PID}" "${BACKEND_TUNNEL_PID}" "${FRONTEND_PID}" "${BACKEND_PID}" "${VISION_PID}"; do
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


resolve_first_existing_file() {
  for candidate in "$@"; do
    if [[ -n "${candidate}" ]] && [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

resolve_vision_model_path() {
  if [[ -n "${VISION_MODEL_PATH}" ]]; then
    printf '%s\n' "${VISION_MODEL_PATH}"
    return 0
  fi
  resolve_first_existing_file \
    "${ROOT_DIR}/models/gemma-4-E4B-it-Q4_K_M.gguf" \
    "${ROOT_DIR}/models/google_gemma-4-E4B-it-Q4_K_M.gguf" \
    "${ROOT_DIR}/models/gemma-4-E4B-it-Q4_0.gguf" \
    "${ROOT_DIR}/models/google_gemma-4-E4B-it-Q4_0.gguf"
}

resolve_vision_mmproj_path() {
  if [[ -n "${VISION_MMPROJ_PATH}" ]]; then
    printf '%s\n' "${VISION_MMPROJ_PATH}"
    return 0
  fi
  resolve_first_existing_file \
    "${ROOT_DIR}/models/mmproj-BF16.gguf" \
    "${ROOT_DIR}/models/mmproj-F16.gguf" \
    "${ROOT_DIR}/models/mmproj-google_gemma-4-E4B-it-bf16.gguf" \
    "${ROOT_DIR}/models/mmproj-google_gemma-4-E4B-it-f16.gguf"
}

vision_warn_or_fail() {
  local message="$1"
  if [[ "${REQUIRE_VISION}" == "1" ]]; then
    echo "Vision bridge required but unavailable: ${message}" >&2
    exit 1
  fi
  echo "Vision bridge warning: ${message}" >&2
}

start_vision_server() {
  if [[ "${VISION_AUTOSTART}" != "1" ]]; then
    if [[ -n "${ARSITRAD_VISION_BASE_URL:-}" ]]; then
      export ARSITRAD_VISION_BASE_URL="${VISION_BASE_URL}"
    fi
    return 0
  fi

  if python - "${VISION_BASE_URL}/health" <<'PY'
import sys, urllib.request
try:
    with urllib.request.urlopen(sys.argv[1], timeout=1) as response:
        raise SystemExit(0 if 200 <= response.status < 500 else 1)
except Exception:
    raise SystemExit(1)
PY
  then
    export ARSITRAD_VISION_BASE_URL="${VISION_BASE_URL}"
    echo "Vision bridge already running at ${VISION_BASE_URL}"
    return 0
  fi

  if ! command -v "${LLAMA_SERVER_BIN}" >/dev/null 2>&1; then
    vision_warn_or_fail "${LLAMA_SERVER_BIN} not found; install llama.cpp or set ARSITRAD_LLAMA_SERVER_BIN"
    return 0
  fi

  local model_path
  local mmproj_path
  if ! model_path="$(resolve_vision_model_path)"; then
    vision_warn_or_fail "Gemma vision model GGUF not found; set ARSITRAD_VISION_MODEL_PATH"
    return 0
  fi
  if ! mmproj_path="$(resolve_vision_mmproj_path)"; then
    vision_warn_or_fail "Gemma vision mmproj GGUF not found; set ARSITRAD_VISION_MMPROJ_PATH"
    return 0
  fi

  : > "${VISION_LOG}"
  echo "Starting Gemma vision bridge on ${VISION_BASE_URL}"
  "${LLAMA_SERVER_BIN}" \
    -m "${model_path}" \
    --mmproj "${mmproj_path}" \
    --host "${VISION_HOST}" \
    --port "${VISION_PORT}" \
    -c "${ARSITRAD_VISION_CTX:-4096}" \
    -ngl "${ARSITRAD_VISION_N_GPU_LAYERS:-999}" \
    >"${VISION_LOG}" 2>&1 &
  VISION_PID=$!
  export ARSITRAD_VISION_BASE_URL="${VISION_BASE_URL}"
  wait_for_url "${VISION_BASE_URL}/health" "vision bridge"
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
: > "${VISION_LOG}"
: > "${BACKEND_TUNNEL_LOG}"
: > "${FRONTEND_TUNNEL_LOG}"

start_vision_server

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
Vision URL:   ${ARSITRAD_VISION_BASE_URL:-metadata-only}

CORS note: api/server.py allows https://*.trycloudflare.com by default.
If you disable the default regex, set:
ARSITRAD_WEB_ALLOWED_ORIGINS=${FRONTEND_TUNNEL_URL}

Logs:
Backend:         ${BACKEND_LOG}
Frontend:        ${FRONTEND_LOG}
Vision:          ${VISION_LOG}
Backend tunnel:  ${BACKEND_TUNNEL_LOG}
Frontend tunnel: ${FRONTEND_TUNNEL_LOG}

Press Ctrl+C to stop backend, frontend, and both tunnels.
EOF

wait
