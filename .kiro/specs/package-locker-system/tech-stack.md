# Tech Stack

Status: chosen for a POC that extends to feature-complete without a rewrite.

## Guiding constraints

- POC now, feature-complete later — favour choices that scale in place.
- Three distinct UIs: master/admin (desktop), delivery agent (mobile), customer (mobile).
- Notification subsystem with a full transaction log (success/failure).
- Concurrency-safe locker allocation (Level 4).
- Single-image deployment: local build → public registry → Ubuntu via Docker.

## Selection

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.12 | Typed, fast to build. |
| API framework | FastAPI + Uvicorn | Typed REST, auto OpenAPI, small footprint. |
| ORM / models | SQLModel (SQLAlchemy core) | One model definition for DB + API schema. |
| Database (POC) | SQLite | Zero setup, ships in the container. |
| Database (later) | PostgreSQL | Connection-string swap via SQLAlchemy; no model rewrite. |
| Concurrency | DB transaction + atomic conditional claim | `UPDATE ... WHERE status='AVAILABLE'`; two agents can never win the same locker. Ports to Postgres `SELECT ... FOR UPDATE SKIP LOCKED`. |
| Frontend | React + TypeScript + Vite | One SPA, three routed views; mobile views are responsive layouts. |
| Styling | Plain CSS | No component-lib dependency for a POC. |
| Notifications | `Notifier` interface + `LogNotifier` | Logs every event to a table shown in admin. Real SMS/email swappable later. |
| Packaging | Multi-stage Dockerfile | Stage 1 builds React, stage 2 runs FastAPI serving API + static. One image, one port. |
| Registry | GitHub Container Registry (public) | Free for public images. |
| Runtime | Docker on Ubuntu | Single `docker run`. |

## Deliberately NOT added (YAGNI)

- No message broker/queue — the notification log is a table.
- No microservices — one deployable artifact.
- No auth provider yet — roles are selected per view; real auth is a documented extension point.
- No separate mobile apps — responsive web.

## Extension points (documented, not built)

- Swap SQLite → Postgres: change `DATABASE_URL`.
- Swap `LogNotifier` → real SMS/email: implement `Notifier`.
- Add authentication/authorization at the API boundary.
- Add new locker/package sizes via the ordered size enum + size spec.
