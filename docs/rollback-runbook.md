# Arsitrad Rollback Runbook

Phase 5 goal: keep rollback boring. If the Next.js workbench fails during demo, use the legacy Streamlit app without touching notebooks, model files, or retrieval data.

## Primary path

Use the Next.js + FastAPI stack first:

```bash
./scripts/run_web_demo.sh
```

Public temporary demo path:

```bash
./scripts/run_cloudflare_demo.sh
```

## Fast rollback path

If the web stack fails, stop the running Next.js/FastAPI processes and start the legacy Streamlit UI:

```bash
./scripts/run_legacy_streamlit.sh
```

Smoke check without starting a browser server:

```bash
./scripts/run_legacy_streamlit.sh --smoke-only
```

Direct legacy command:

```bash
streamlit run legacy/streamlit_app.py
```

Compatibility command retained for old notes/scripts:

```bash
streamlit run ui/app.py
```

## Rollback decision table

| Symptom | Use rollback? | Action |
|---|---:|---|
| Next.js page does not load | Yes | Run `./scripts/run_legacy_streamlit.sh` |
| FastAPI `/health` fails | Maybe | Try legacy Streamlit; it uses Python directly |
| Browser CORS error with public tunnel | Maybe | Use legacy Streamlit or rerun `./scripts/run_cloudflare_demo.sh` |
| `/health` shows `model_exists=false` | No | Bridge is healthy; app will run fallback/retrieval mode |
| QA answer cites irrelevant chunks | No | Retrieval quality issue, not a UI rollback trigger |
| Permit/Cooling/Disaster/Settlement module UI breaks | Maybe | Use legacy Streamlit helper tabs for the demo |

## Pre-demo checks

```bash
./scripts/run_web_demo.sh --smoke-only
./scripts/run_legacy_streamlit.sh --smoke-only
python -m pytest tests/test_api_server.py tests/test_ui_smoke.py tests/test_demo_scripts.py -q
cd web && npm run build
```

## What not to do during rollback

- Do not edit notebooks.
- Do not rewrite Git history.
- Do not delete `web/`, `api/`, or `legacy/`.
- Do not change env/auth/cost/routing settings mid-demo unless you know exactly why.

## Current structure

- Product UI: `web/`
- API bridge: `api/server.py`
- Legacy fallback: `legacy/streamlit_app.py`
- Old Streamlit compatibility entrypoint: `ui/app.py`
