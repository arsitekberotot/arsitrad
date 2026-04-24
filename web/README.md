# Arsitrad Web UI

Proper Next.js + shadcn-style frontend for Arsitrad.

The Python source of truth remains in the repo root. This frontend talks to `api/server.py` through `NEXT_PUBLIC_API_BASE_URL`.

## One-command local demo

From the repo root:

```bash
./scripts/run_web_demo.sh
```

Open http://127.0.0.1:3000

## Manual local run

1. Start the Python API from the repo root:

```bash
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

2. In this `web/` directory, install dependencies and set env:

```bash
cp .env.example .env.local
npm install
```

3. Start the frontend:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open http://127.0.0.1:3000

## Public demo

Use the repo-level Cloudflare helper when you intentionally want temporary public URLs:

```bash
./scripts/run_cloudflare_demo.sh
```

See `../docs/demo-deployment.md` for the full runbook.

## Validation

```bash
npm run lint
npm run build
```
