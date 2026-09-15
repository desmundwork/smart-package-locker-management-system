# Engineering Conventions & Guardrails

Applies to every task. Keeps the build consistent, reviewable, and commit-clean.

## Principles
- POC now, feature-complete later — choices scale in place (SQLite→Postgres by URL, a `Notifier` interface, an ordered size enum). No speculative abstractions (YAGNI).
- Single source of truth: size spec, size ordering, timezone handling, and charge rules each live in exactly one place. The frontend reads spec data from the API, never hardcoded.
- Correctness over cleverness: the concurrency guarantee and the charge math are load-bearing — keep them simple, explicit, independently tested.
- Every outcome is observable: success and failure both write a `NotificationLog` row; the admin view is the audit surface.

## Backend
- Python 3.12, full type hints. FastAPI + SQLModel + Uvicorn.
- Time is UTC always: produce with `now_utc()`, normalize DB reads with `as_utc()` before comparing/subtracting. SQLite returns naive; `as_utc` is the single reconciliation point.
- Enums, not string literals. Allocation reads `SIZE_ORDER`/`size_rank`, never hardcoded names.
- Config is env-driven and centralized in `config.Settings`; defaults let the app run with zero setup.
- Expected domain failures are normal responses (boolean flag + human message), not exceptions. HTTP error codes only for genuinely invalid requests (unknown size → 422; unmatched `/api/*` → 404 JSON).
- State transitions two requests could race on use a conditional `UPDATE ... WHERE status=<expected>` and check `rowcount` — for both claim (AVAILABLE→HELD) and expiry release (HELD→AVAILABLE).
- Pickup codes: `secrets`-random 6-char alphanumeric, unique-constrained.
- Keep routers thin: parse → call service → return schema. Logic lives in `services.py`/`charges.py`.

## Frontend
- React + TypeScript + Vite, one SPA, plain CSS.
- `api.ts` is the only place that talks to the backend; response shapes mirror backend schemas.
- No hardcoded domain data — sizes/dimensions/volumes/labels come from `GET /api/sizes`; degrade gracefully if it fails.
- Every async handler catches errors and surfaces a message; never swallow a thrown fetch in `finally`.
- Live views poll (3s); pause polling mid multi-step transaction.
- Accessibility: selections use `radiogroup`/`radio` + `aria-checked`; AAA text contrast; WCAG 1.4.11 for non-text UI.

## Testing & verification
- Tests land with the feature, in the same commit.
- Unit-test pure logic (charge tiers) and verify end-to-end via the API (backdated stored_at).
- Concurrency is proven: many concurrent requests vs fewer lockers → exactly N distinct succeed, rest get "no locker", none double-assigned — same-size and mixed-size.
- Before every commit: `pytest` green, `tsc --noEmit` + `npm run build` clean. Exit 0 is not proof — assert on actual values. Clean up temp DBs.

## Git & commits
- Conventional Commits (`feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `build`); scope optional.
- One logical change per commit; each commit leaves the repo green. Never commit a broken build.
- Stage specific files, not `git add .`. Review the diff.
- Commit body states what changed, how it was verified, and the requirement IDs satisfied.
- Branch + PR; never force-push shared branches, skip hooks, or commit secrets/`*.db`.

## Security & ops
- Container runs as non-root; SQLite under a declared `VOLUME`.
- No secrets in the image/repo; config injected at runtime.
- Pin dependencies. Treat external input as untrusted; validate sizes; never echo secrets.
- Healthcheck hits `/api/health`.
