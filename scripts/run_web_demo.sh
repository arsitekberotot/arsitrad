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
API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"
SMOKE_ONLY=0

if [[ "${1:-}" == "--smoke-only" ]]; then
  SMOKE_ONLY=1
fi

BACKEND_LOG="${ARSITRAD_BACKEND_LOG:-/tmp/arsitrad-api.log}"
FRONTEND_LOG="${ARSITRAD_FRONTEND_LOG:-/tmp/arsitrad-next.log}"
LLAMA_SERVER_BIN="${ARSITRAD_LLAMA_SERVER_BIN:-llama-server}"
REQUIRE_VISION="${ARSITRAD_REQUIRE_VISION:-0}"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${VISION_PID}" ]] && kill -0 "${VISION_PID}" 2>/dev/null; then
    kill "${VISION_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM


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

cd "${ROOT_DIR}"

if [[ ! -d "web/node_modules" ]]; then
  echo "web/node_modules missing; run: cd web && npm install" >&2
  exit 1
fi

: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"
: > "${VISION_LOG}"

start_vision_server

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
Vision:   ${ARSITRAD_VISION_BASE_URL:-metadata-only}

Logs:
Backend:  ${BACKEND_LOG}
Frontend: ${FRONTEND_LOG}
Vision:   ${VISION_LOG}

Press Ctrl+C to stop both processes.
EOF

if [[ "${SMOKE_ONLY}" == "1" ]]; then
  echo "Smoke-only mode complete; stopping processes."
  exit 0
fi

wait
