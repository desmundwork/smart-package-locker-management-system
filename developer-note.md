# Developer Note

A short note to the reviewer on what this delivers, how it's built, and how AI
tooling was used.

## 1. Scope — what it implements

This solution implements the full challenge. All four levels are covered and
exercised by tests:

- **Level 1 — storage:** smallest-fitting locker allocation with a unique pickup
  code (two-phase: reserve then confirm).
- **Level 2 — retrieval:** pickup by locker id + code, with invalid/reused-code
  handling (two-phase: unlock then confirm-closed).
- **Level 3 — storage charges:** tiered rule (X/day for days 1–5, 2X for 6–10,
  3X for day 11+), 24h day rounded up, returned with the pickup and an audit
  (stored/retrieved timestamps + billable days).
- **Level 4 — concurrency:** an atomic conditional claim so two agents can never
  get the same locker, proven under load for both same-size and mixed-size
  contention.

On top of the required goals it adds: a notification/transaction log, a size
catalogue with physical dimensions and volume, hold expiry for abandoned
reservations, and three role-tailored UIs (admin, delivery agent, customer).
Requirement-to-code mapping lives in `.kiro/specs/package-locker-system/`.

## 2. Why it's a POC

It is deliberately structured as a proof-of-concept so the system's feasibility
is easy to review and test, while leaving a clean path to feature-complete:

- **Runs with zero setup** — SQLite by default, a single command to start, a
  single Docker image serving both the API and the UI.
- **Easy to reason about** — thin routers over a small service layer, one
  data-model file, a pure charge function, and a swappable notification
  interface.
- **Extension points are documented, not prematurely built** — SQLite → Postgres
  by connection string, `LogNotifier` → a real SMS/email provider, new locker
  sizes via one ordered enum + spec, and the REST boundary as the place to add
  real authentication. See `.kiro/specs/package-locker-system/tech-stack.md`.

## 3. AI tooling

**Which tool(s)?** Kiro — an AI-powered development environment. https://kiro.dev

**How they were used.** Kiro was used spec-first and incrementally, not as a
one-shot generator. The flow was: agree on requirements, then a design and a
tech stack, then a sequenced task plan, then implement one task at a time. Each
step was reviewed and refined in conversation before moving on, and the assistant
ran the test suite and the frontend type-check/build as a gate before each
commit. Where an approach was wrong, it was corrected in dialogue rather than
accepted blindly.

**What was AI-assisted.** Effectively the whole build was produced with Kiro
under human direction and review:

- Backend: FastAPI app, SQLModel data model, the allocation/retrieval/charge
  logic, the atomic concurrency claim, hold expiry, and the notification
  subsystem.
- Frontend: the React + TypeScript SPA and its three views (admin, agent,
  customer) including the live locker recommendation and the visual picker.
- Tests: unit, API-level, and concurrency tests.
- Packaging and docs: the multi-stage Dockerfile, deployment guides, the spec
  documents, and this note.
- The staged git history itself (one reviewable commit per milestone) was
  planned and executed with the assistant.

The human role was setting intent, reviewing each increment, catching issues,
and making the design and scope decisions.

**Prompts / workflow worth sharing.** The workflow that worked well:

1. Start from a spec, not code. Ask for requirements (EARS-style), then a
   design and tech stack, then a task breakdown — and review each before
   implementation.
2. Implement in small, verifiable steps. A representative instruction was to
   "build the system from scratch with proper stages between commits so it's
   clear for code review later," which produced the staged history in this repo.
3. Review and correct in the loop. Earlier iterations were reviewed with prompts
   like "thoroughly review our implementation and suggest improvements," then
   fixes were applied and re-verified.
4. Gate every commit on green tests and a clean build; keep expected domain
   failures as normal responses and prove concurrency with real threads.

## 4. Notes to the reviewer

- **Read the git history in order.** It is intentionally staged — one logical
  commit per milestone (spec → model → services → flows → charges → concurrency
  → sizes → UI → serve → Docker → docs → acceptance), tagged `v0.1.0`. Each
  commit message records what changed, how it was verified, and the requirement
  IDs it satisfies.
- **Run the backend tests:**
  ```bash
  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
  .venv/bin/pytest
  ```
- **Build/verify the frontend:**
  ```bash
  cd frontend && npm install && npm run build   # or: npx tsc --noEmit
  ```
- **Run the whole thing in one process** (API + built SPA): see `README.md`
  "Run locally" or `docker run` per `deployment-docs/`.
- **Docker build verified.** The image builds via the multi-stage `Dockerfile`
  and was run end-to-end: `/api/health` is OK, the SPA and `/docs` are served,
  unknown `/api/*` paths return a JSON 404, the full create → hold → complete →
  open (charge) → close lifecycle works, the container runs as the non-root
  `appuser`, and the `HEALTHCHECK` reports `healthy`.
- **Published.** The source is pushed to GitHub and the container image is
  published to GHCR (see `deployment-docs/deploy.md` for pull/run instructions).
- **Where to look:** business logic in `backend/app/services.py` and
  `backend/app/charges.py`; the concurrency claim in `hold_locker`; the spec and
  conventions under `.kiro/`.
