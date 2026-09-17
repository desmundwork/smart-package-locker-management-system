# Smart Package Locker Management System

A POC (built to extend to feature-complete) that lets delivery agents store packages in size-appropriate lockers and customers retrieve them with a pickup code. Implements Levels 1–4 of the Everest Engineering coding challenge (basic storage, retrieval, tiered storage charges, concurrency), plus a two-phase store/pickup model, hold expiry, per-size dimensions, and role-tailored UX.

## Layout

```
backend/           FastAPI + SQLModel API and business logic
  app/             models, db, config, services, charges, notifier, routers/
  tests/           pytest (charges, API flow, concurrency, expiry, SPA routing)
frontend/          React + TypeScript + Vite SPA (3 views)
  src/views/       Landing, Admin (desktop), Agent (mobile), Customer (mobile)
deployment-docs/   build.md, run.md, deploy.md (local -> GHCR -> Ubuntu)
.kiro/specs/       requirements, design, tasks, tech-stack
.kiro/steering/    engineering conventions
Dockerfile         multi-stage build (SPA -> Python runtime, one image)
```

## Locker sizes

Each size has a fixed interior spec (defined once in `backend/app/models.py` as `SIZE_DIMENSIONS` and served via `GET /api/sizes`, so the UI never hardcodes it). Dimensions are W × D × H in centimetres; volume in litres.

| Size | Dimensions (W×D×H) | Volume | Fits |
|------|--------------------|--------|------|
| SMALL | 30 × 40 × 15 cm | 18 L | a shoebox or small parcel |
| MEDIUM | 45 × 55 × 30 cm | 74.2 L | a backpack or a couple of shoeboxes |
| LARGE | 60 × 70 × 45 cm | 189 L | a carry-on suitcase or large box |

To add a size, append it to `SIZE_ORDER`, `SIZE_DIMENSIONS`, and `SIZE_LABELS`; it flows through allocation, the API, and the UI automatically.

## Views

- `/admin` — create/manage lockers, visual locker map, transaction log (desktop).
- `/agent` — random incoming parcel with a live smallest-locker recommendation, two-phase store (mobile).
- `/customer` — visual locker picker, two-phase pickup with storage charge (mobile).
- `/docs` — auto-generated OpenAPI (opens in a new tab).
- `GET /api/sizes` — locker size catalogue (dimensions, volume, fit hints).

## Run locally (backend + built SPA in one process)

```bash
# 1. build the SPA
cd frontend && npm install && npm run build
# 2. put the build where the backend serves it
cp -r dist ../backend/static
# 3. run the API (serves the SPA too)
cd ../backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
# open http://localhost:8000
```

For backend-only dev with hot reload, run `frontend`'s `npm run dev` (proxies `/api` and `/docs` to :8000) and `backend/run-dev.sh` separately.

## Run with Docker

```bash
docker build -t smart-package-locker .
docker run --rm -p 8000:8000 smart-package-locker
```

The container runs as a non-root user and stores its SQLite DB at `/data/locker.db`. To persist data across restarts, mount a volume:

```bash
docker run --rm -p 8000:8000 -v locker-data:/data smart-package-locker
```

See `deployment-docs/` for GHCR publishing and Ubuntu deployment.

## Test

```bash
cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest
```

## Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `DATABASE_URL` | `sqlite:///./locker.db` (local) / `sqlite:////data/locker.db` (Docker) | DB connection (swap to Postgres later) |
| `STORAGE_UNIT_RATE` | `1` | X in the tiered storage-charge rule |
| `HOLD_TIMEOUT_SECONDS` | `120` | Unconfirmed agent holds older than this are auto-released (0 disables) |
| `PORT` | `8000` | HTTP port |
