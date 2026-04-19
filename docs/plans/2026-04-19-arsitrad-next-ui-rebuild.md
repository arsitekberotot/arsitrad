# Arsitrad Next.js + shadcn UI Rebuild Plan

> For Hermes: use subagent-driven-development thinking, but keep this implementation additive and do not break the existing Streamlit path.

Goal: ship a proper web UI for Arsitrad using Next.js + shadcn-style components, backed by a small Python API that wraps the existing ArsitradAnswerEngine.

Architecture:
- Keep the current Python retrieval/inference code as the source of truth.
- Add a minimal FastAPI service for health + ask endpoints.
- Add a new `web/` Next.js app that talks to the Python API via `NEXT_PUBLIC_API_BASE_URL`.
- Keep `ui/app.py` intact as fallback/demo path.

Tech stack:
- Python: FastAPI, uvicorn, existing pipeline/inference modules
- Frontend: Next.js App Router, TypeScript, Tailwind, shadcn-style component structure, lucide-react

---

## Task 1: Add the API surface
- Create `api/server.py`
- Add request/response models for chat questions and structured answers
- Expose `GET /health` and `POST /api/ask`
- Cache `ArsitradAnswerEngine` so it is not recreated every request

## Task 2: Add Python tests for the API contract
- Create `tests/test_api_server.py`
- Mock the engine so tests stay fast
- Verify health endpoint, ask endpoint, and response serialization

## Task 3: Scaffold the web app
- Create `web/` using Next.js + TypeScript + Tailwind + App Router
- Add project config, scripts, env example, and core app shell

## Task 4: Build the shadcn-style UI
- Create reusable UI primitives in `web/src/components/ui/`
- Build landing shell, sidebar/status cards, chat panel, answer sections, and source cards
- Render confidence, mode, structured sections, and citations cleanly

## Task 5: Wire frontend to backend
- Add typed API client in `web/src/lib/api.ts`
- Handle loading, errors, and empty states
- Add starter prompts and helper quick actions

## Task 6: Validate locally
- Python: compile + focused tests
- Web: install dependencies, lint, build
- Smoke-check local integration docs/commands

## Task 7: Ship
- Review diff
- Commit cleanly
- Push to `main`
