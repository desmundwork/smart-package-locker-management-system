# Acceptance — v0.1.0

Final end-to-end verification of the initial release.

## Automated

- **Backend:** `pytest` — 55 passed. Covers models, notifications, locker
  management, two-phase store (hold/complete/cancel), two-phase pickup
  (open/close), tiered charges (unit + via API), same-size and mixed-size
  concurrency, hold expiry (incl. concurrent sweeps), size catalogue, and SPA
  routing (client fallback + API-safe 404).
- **Frontend:** `tsc --noEmit` clean; `npm run build` succeeds.

## Manual smoke (single process: FastAPI serving the built SPA)

| Check | Result |
|-------|--------|
| `GET /api/health` | 200 `{status:ok}` |
| `GET /admin` serves SPA shell | 200, index.html |
| `GET /api/<unknown>` | 404 `application/json` (not the SPA) |
| `GET /docs` (OpenAPI) | 200 |
| create → hold (S-001) | held |
| complete | locker OCCUPIED |
| open with code | opened, charge 1.0, 1 billable day |
| close | locker AVAILABLE |

## Requirement coverage

All requirements 1–12 exercised by the suite above and the manual smoke. See
`tasks.md` for the milestone → requirement mapping.
