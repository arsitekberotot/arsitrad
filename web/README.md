# Arsitrad Web UI

Proper Next.js + shadcn-style frontend for Arsitrad.

## Local run

1. Start the Python API from the repo root:

```bash
python -m uvicorn api.server:app --reload --port 8000
```

2. In this `web/` directory, install dependencies and set env:

```bash
cp .env.example .env.local
npm install
```

3. Start the frontend:

```bash
npm run dev
```

Open http://127.0.0.1:3000
