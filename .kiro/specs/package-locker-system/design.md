# Design — Smart Package Locker Management System

Implements `requirements.md` using the stack in `tech-stack.md`.

## 1. Architecture

One deployable container, one port:

```
┌─────────────────────────────────────────────────┐
│  Container (single image, port :8000)             │
│                                                   │
│  FastAPI (Uvicorn)                                │
│   ├── /api/*        REST endpoints                │
│   ├── /docs         OpenAPI (auto, new tab)       │
│   └── /* (static)   React SPA build               │
│                                                   │
│  Routers (thin)  →  Services (logic)              │
│   lockers, packages, pickups, notifications,      │
│   sizes                                           │
│      ├── allocation (two-phase store, atomic)     │
│      ├── retrieval (two-phase pickup, charges)    │
│      ├── expiry sweep (atomic release)            │
│      └── Notifier (protocol) → LogNotifier        │
│                                                   │
│  charges.py  (pure tiered-charge function)        │
│                                                   │
│  SQLModel / SQLAlchemy                            │
│   └── SQLite file under a VOLUME | Postgres later │
└─────────────────────────────────────────────────┘
```

The SPA is built at image-build time and served as static files by FastAPI, so
there is no separate frontend server. Non-root runtime user; healthcheck on
`/api/health`.

## 2. Data model

```
Locker
  id: str (PK, "S-001" / "M-001" / "L-001")
  size: Size {SMALL, MEDIUM, LARGE}           # ordered SMALL<MEDIUM<LARGE
  status: LockerStatus {AVAILABLE, HELD, OCCUPIED, OPEN}
  created_at: datetime (UTC)

Package
  id: str (PK, "P-<hex>")
  size: Size
  locker_id: str (FK → Locker.id, nullable)
  pickup_code: str (unique, indexed, 6-char alnum)
  status: PackageStatus {PENDING, STORED, RETRIEVED}
  held_at: datetime (UTC)                      # reservation time
  stored_at: datetime | null                   # set on confirm; charge clock start
  retrieved_at: datetime | null
  storage_charge: float | null

NotificationLog
  id: int (PK, autoincrement)
  ts: datetime (UTC)
  event_type: EventType {STORE_ATTEMPT, HOLD_SUCCESS, HOLD_FAILURE,
                         STORE_SUCCESS, STORE_CANCELLED, HOLD_EXPIRED,
                         PICKUP_SUCCESS, PICKUP_FAILURE, PICKUP_CLOSED, CODE_SEND}
  outcome: Outcome {SUCCESS, FAILURE}
  locker_id: str | null
  package_id: str | null
  detail: str
```

**Status lifecycle**

```
Locker:  AVAILABLE ──hold──▶ HELD ──complete──▶ OCCUPIED ──open──▶ OPEN ──close──▶ AVAILABLE
                     ▲          │ cancel / expiry
                     └──────────┘
Package: (none) ──hold──▶ PENDING ──complete──▶ STORED ──open──▶ RETRIEVED
                              │ cancel / expiry → deleted
```

**Size specification (single source of truth)**

- `SIZE_ORDER = [SMALL, MEDIUM, LARGE]` drives the fit rule via `size_rank`.
- `SIZE_DIMENSIONS[size] = Dimensions(width_cm, depth_cm, height_cm)` with a computed `volume_litres = w*d*h/1000` (rounded 1 dp).
- `SIZE_LABELS[size]` = plain-language fit hint.
- Fit rule: a package fits when `size_rank(locker.size) >= size_rank(package.size)`.
- Add a size by appending to these three structures only.

Reference dimensions: SMALL 30×40×15 (18 L), MEDIUM 45×55×30 (74.2 L), LARGE 60×70×45 (189 L).

**Timezone rule:** `now_utc()` produces aware UTC; `as_utc()` normalizes any datetime (SQLite returns naive) before any comparison/subtraction. Used by the charge function and the expiry sweep.

## 3. Allocation — two-phase store + concurrency (Levels 1 & 4, hold expiry)

**Phase 1 — hold** (`POST /api/packages/hold`), package size S:
1. Run the lazy expiry sweep, then log `STORE_ATTEMPT`.
2. Select `status=AVAILABLE AND size_rank>=rank(S)`, ordered by `(size_rank, id)` — smallest fit first.
3. **Atomic conditional claim** on the first candidate: `UPDATE locker SET status='HELD' WHERE id=? AND status='AVAILABLE'`.
4. IF `rowcount == 0` (lost the race) → rollback, retry the next candidate.
5. IF claimed → create `Package(PENDING, held_at=now, unique pickup_code)`, commit, log `HOLD_SUCCESS`. Return `{held, package_id, locker_id, pickup_code, message}`.
6. IF no candidate remains → log `HOLD_FAILURE`, return `held=false` with a message.

The conditional `WHERE status='AVAILABLE'` is the concurrency guarantee. Maps to Postgres `SELECT ... FOR UPDATE SKIP LOCKED`; on SQLite the serialized write transaction gives the same result.

**Phase 2 — complete** (`POST /api/packages/complete`): if still PENDING → STORED, `stored_at=now` (charge clock starts here), locker HELD→OCCUPIED, log `STORE_SUCCESS` + `CODE_SEND`. Otherwise "nothing to confirm".

**Cancel** (`POST /api/packages/cancel`): pending package discarded, locker HELD→AVAILABLE, log `STORE_CANCELLED`.

**Hold expiry** (lazy sweep at start of hold/list): for each PENDING package with `as_utc(held_at)` older than `HOLD_TIMEOUT_SECONDS`, **atomically release** `UPDATE locker SET status='AVAILABLE' WHERE id=? AND status='HELD'`. Only the sweep whose `rowcount==1` deletes the package and logs `HOLD_EXPIRED`, committing per hold — concurrent sweeps release each hold exactly once.

**Pickup code:** `secrets`-random 6-char alphanumeric, unique-constrained.
**Locker id:** `<prefix>-<n:03d>` where prefix ∈ {S,M,L}, numbered per size.

## 4. Retrieval + storage charge (Levels 2 & 3)

**Phase 1 — open** (`POST /api/pickups/open`) with (locker_id, pickup_code):
1. Find `Package` where `locker_id=? AND pickup_code=? AND status=STORED`.
2. IF none → log `PICKUP_FAILURE`, return `opened=false`, unlock nothing.
3. ELSE compute `charge` + `billable_days`; package RETRIEVED, `retrieved_at=now`, `storage_charge=charge`; locker OCCUPIED→**OPEN**; commit; log `PICKUP_SUCCESS`. Return `{opened, locker_id, storage_charge, stored_at, retrieved_at, billable_days, message}`.

**Phase 2 — close** (`POST /api/pickups/close`): locker OPEN→AVAILABLE, log `PICKUP_CLOSED`. Reusable only after this step.

**Charge (pure function, `charges.py`):** X = `STORAGE_UNIT_RATE` (default 1).
- `billable_days = ceil(elapsed_seconds / 86400)` using `as_utc` both ends; `<=0` → 0.
- Sum per day: days 1–5 → X, days 6–10 → 2X, day 11+ → 3X.
- Unit-tested at tier boundaries **and** verified end-to-end via the pickup API by backdating `stored_at`.

## 5. REST API

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | `/api/lockers` | Admin | Create locker `{size}` → `LockerOut` (incl. dimensions) |
| GET | `/api/lockers` | any | List lockers + status + dimensions |
| GET | `/api/sizes` | any | Size catalogue: dimensions, volume, fit label |
| POST | `/api/packages/hold` | Agent | Phase 1: reserve smallest fit → `{package_id, locker_id, pickup_code}` or `held:false` |
| POST | `/api/packages/complete` | Agent | Phase 2: confirm (HELD→OCCUPIED, set stored_at) |
| POST | `/api/packages/cancel` | Agent | Release a hold (HELD→AVAILABLE, discard pending) |
| POST | `/api/pickups/open` | Customer | Phase 1: validate code, unlock (OCCUPIED→OPEN), finalize charge |
| POST | `/api/pickups/close` | Customer | Phase 2: confirm shut (OPEN→AVAILABLE) |
| GET | `/api/notifications` | Admin | Transaction log, newest first (`limit` param) |
| GET | `/api/health` | ops | Liveness `{status, version}` |

Expected domain failures return a normal body with a boolean flag + message; only truly invalid requests use HTTP error codes (unknown size → 422; unmatched `/api/*` GET → 404 JSON, not the SPA shell).

## 6. UI (React SPA, one build)

| Route | View | Device | Contents |
|-------|------|--------|----------|
| `/` | Landing | any | All three views side by side (collapsible columns); links + "API docs" (new tab). |
| `/admin` | Master system view | Desktop | Create form (size dims/volume); visual locker map (grouped by size, footprint scaled, color=status); locker table; transaction log (auto-refresh). |
| `/agent` | Delivery agent | Mobile | Random incoming parcel + spec; "Change package"; live smallest-fit recommendation; no-locker handling; two-phase store with copyable pickup code. |
| `/customer` | Customer | Mobile | Visual selection of available lockers (grouped like the admin map); code-only entry; two-phase pickup; charge + billable-day display. |

- The API client (`api.ts`) is the sole backend interface; `format.ts` holds shared display formatters. Size spec comes from `/api/sizes`. Views poll (3s), pausing mid-transaction. Selections are accessible `radiogroup`s.

## 7. Concurrency test strategy

- **Same-size:** N holds vs M<N same-size lockers → exactly M succeed, distinct, N−M rejected.
- **Mixed-size:** many requests across sizes vs a mixed pool → exactly pool-size succeed, distinct, surplus rejected, none left available.
- **Expiry:** concurrent sweeps on one expired hold → released once, one `HOLD_EXPIRED`.
- File SQLite + `busy_timeout` so writers serialize.

## 8. Error handling

- Unknown/invalid size → 422 (schema validation).
- Retrieval with no match → `opened:false` + `PICKUP_FAILURE`.
- "No suitable locker" → `held:false` (expected outcome).
- Unmatched `/api/*` → JSON 404 (SPA catch-all excludes `api` prefix).
- Every outcome writes a `NotificationLog` row.

## 9. Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `DATABASE_URL` | `sqlite:///./locker.db` (local) / `sqlite:////data/locker.db` (Docker) | DB connection |
| `STORAGE_UNIT_RATE` | `1` | X in the tiered charge rule |
| `HOLD_TIMEOUT_SECONDS` | `120` | Unconfirmed holds older than this auto-release (0 disables) |
| `PORT` | `8000` | HTTP port |

## 10. Packaging & deployment

- Multi-stage Dockerfile: stage 1 builds the SPA (`node`), stage 2 runs FastAPI (`python-slim`) serving API + `static/`.
- Runs as non-root `appuser`; SQLite under `/data` declared as a `VOLUME`; `DATABASE_URL` points there; `HEALTHCHECK` hits `/api/health`.
- `deployment-docs/`: build.md, run.md, deploy.md (registry push → Ubuntu pull/run).
