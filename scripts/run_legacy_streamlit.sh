#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEGACY_APP="${ROOT_DIR}/legacy/streamlit_app.py"
SMOKE_ONLY=0

if [[ "${1:-}" == "--smoke-only" ]]; then
  SMOKE_ONLY=1
  shift
fi

cd "${ROOT_DIR}"

if [[ ! -f "${LEGACY_APP}" ]]; then
  echo "Legacy Streamlit app not found: ${LEGACY_APP}" >&2
  exit 1
fi

if [[ "${SMOKE_ONLY}" == "1" ]]; then
  python - <<'PY'
from legacy import streamlit_app
from ui import app as compatibility_app

assert streamlit_app.build_confidence_label(0.8) == "Tinggi"
assert compatibility_app.build_base_css() == streamlit_app.build_base_css()
print("legacy Streamlit fallback import smoke passed")
PY
  exit 0
fi

if ! command -v streamlit >/dev/null 2>&1; then
  echo "Missing streamlit command. Install requirements first:" >&2
  echo "python -m pip install -r requirements.txt" >&2
  exit 1
fi

echo "Starting legacy Streamlit fallback: ${LEGACY_APP}"
echo "Preferred product UI is still Next.js: ./scripts/run_web_demo.sh"
exec streamlit run "${LEGACY_APP}" "$@"
