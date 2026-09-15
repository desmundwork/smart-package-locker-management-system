# Implementation Plan — Smart Package Locker Management System

Each task is incremental, ends at a green committable state, and references the
requirements it satisfies. Complete in order; each builds on the previous. One
task ≈ one commit (Conventional Commits). Backend `pytest` green and frontend
`tsc --noEmit` + `npm run build` clean before each commit.

## Phase A — Foundations

- [ ] 1. Backend scaffold — FastAPI app, env-driven config, `/api/health`, deps, dev run script.
  - _Requirements: 12.1–12.2, 11.5_
- [ ] 2. Data model + DB layer — SQLModel models, enums, size ordering, `now_utc`/`as_utc`; engine + create-tables on startup.
  - _Requirements: 1.1, 3.7–3.8, 8.6, 12_

## Phase B — Locker management & audit

- [ ] 3. Notification subsystem — `Notifier` protocol + `LogNotifier`; `GET /api/notifications` (newest first).
  - _Requirements: 8.1–8.6_
- [ ] 4. Locker management (Admin) — create (per-size ids) + list; `POST/GET /api/lockers`.
  - _Requirements: 1.1–1.5_

## Phase C — Store & retrieve (Levels 1 & 2)

- [ ] 5. Smallest-fit hold (phase 1) — atomic conditional claim with retry; unique pickup code; `POST /api/packages/hold`.
  - _Requirements: 3.1–3.4, 3.7–3.8, 8.1_
- [ ] 6. Complete + cancel (phase 2) — `POST /api/packages/complete|cancel`.
  - _Requirements: 3.5–3.6_
- [ ] 7. Two-phase pickup — `POST /api/pickups/open|close`.
  - _Requirements: 5.1–5.6, 10.1_
- [ ] 8. End-to-end flow test — create → hold → complete → open → close; invalid cases.
  - _Requirements: 3.x, 5.x, 8.x, 10.1_

## Phase D — Charges & concurrency (Levels 3 & 4)

- [ ] 9. Tiered storage charge — pure function + audit fields in pickup response; unit + API tests.
  - _Requirements: 6.1–6.7_
- [ ] 10. Concurrency proof — same-size and mixed-size tests.
  - _Requirements: 7.1–7.6_
- [ ] 11. Hold expiry with atomic release — lazy sweep; concurrent-sweep test.
  - _Requirements: 4.1–4.6_

## Phase E — Size specification

- [ ] 12. Dimensions & volume — size catalogue, `GET /api/sizes`, enriched `LockerOut`.
  - _Requirements: 2.1–2.5_

## Phase F — Frontend

- [ ] 13. SPA scaffold + typed API client + format helpers + base styles.
  - _Requirements: 9d.1_
- [ ] 14. Admin view (desktop) — create form, locker map, table, live log.
  - _Requirements: 9a.1–9a.4, 2.3_
- [ ] 15. Agent view (mobile) — random package, live recommendation, no-locker handling, two-phase store.
  - _Requirements: 9b.1–9b.6_
- [ ] 16. Customer view (mobile) — visual picker, code-only entry, two-phase pickup, charge display.
  - _Requirements: 9c.1–9c.5, 6.6_

## Phase G — Serve, package, deploy

- [ ] 17. Serve SPA from FastAPI — catch-all with API-safe 404; routing tests.
  - _Requirements: 11.2, 10.3, 9d.2_
- [ ] 18. Containerize — multi-stage Dockerfile, non-root, volume, healthcheck; `.dockerignore`.
  - _Requirements: 11.1, 11.3–11.5_
- [ ] 19. Deployment docs + README — build/run/deploy guides, project README.
  - _Requirements: 11.6–11.7_

## Phase H — Final verification

- [ ] 20. Acceptance pass — full suite green; smoke of all three views end-to-end.
  - _Requirements: all_
