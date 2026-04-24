# Arsitrad Web Demo Deployment Runbook

This is the Phase 4 demo path for the Next.js + FastAPI version of Arsitrad.

## Default local demo

Use this when the browser is on the same machine as the app.

```bash
./scripts/run_web_demo.sh
```

It starts:

- FastAPI: `http://127.0.0.1:8000`
- Next.js: `http://127.0.0.1:3000`

Smoke-only mode starts both services, verifies readiness, then stops them:

```bash
./scripts/run_web_demo.sh --smoke-only
```

Useful env overrides:

```bash
ARSITRAD_BACKEND_PORT=8001 ARSITRAD_FRONTEND_PORT=3001 ./scripts/run_web_demo.sh
```

## Public TryCloudflare demo

Use this only when you intentionally want a public temporary demo URL.
It creates two public tunnels:

- frontend tunnel -> local Next.js on port `3000`
- backend tunnel -> local FastAPI on port `8000`

```bash
./scripts/run_cloudflare_demo.sh
```

The script prints:

- `Frontend URL` — give this to the reviewer/demo audience.
- `Backend URL` — used internally by the frontend JavaScript.

`api/server.py` allows `https://*.trycloudflare.com` origins by default, so the two-tunnel setup works without editing tracked config.

## Manual commands

If you do not want the scripts, run the two apps manually.

Terminal 1:

```bash
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Verification checklist

Before a demo, verify:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/bootstrap
cd web && npm run build
python -m pytest tests/test_api_server.py tests/test_ui_smoke.py -q
```

In the browser:

1. Runtime panel shows API connected.
2. Sparse index shows ready.
3. Submit one Permit Navigator request.
4. Submit one Regulation QA question.
5. Confirm answer cards and citation controls render.
6. Check browser console for errors.

## Rollback path

If the Next.js/FastAPI stack fails during demo, switch to the legacy Streamlit fallback:

```bash
./scripts/run_legacy_streamlit.sh
```

Full rollback checklist: `docs/rollback-runbook.md`.

## Known runtime notes

- If `/health` says `model_exists=false`, the web bridge is still healthy; QA runs fallback/retrieval mode.
- If QA cites an irrelevant chunk, that is retrieval-ranking work, not a deployment failure.
- Legacy Streamlit fallback remains available:

```bash
./scripts/run_legacy_streamlit.sh
streamlit run legacy/streamlit_app.py
streamlit run ui/app.py
```

## Do not commit local runtime files

Logs are written to `/tmp` by default:

- `/tmp/arsitrad-api.log`
- `/tmp/arsitrad-next.log`
- `/tmp/arsitrad-api-cloudflared.log`
- `/tmp/arsitrad-web-cloudflared.log`
