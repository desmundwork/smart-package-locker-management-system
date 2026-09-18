# Smart Package Locker — Production

Productionized deployment of the
[Smart Package Locker POC](https://github.com/desmundwork/smart-package-locker-management-system),
adding authentication, role-based authorization, and a per-view subdomain
split, served behind the Caddy SSL terminator.

| Environment | URL | Notes |
|-------------|-----|-------|
| **POC** | https://smart-locker-poc.yeng.click | unchanged single-image POC, all views open |
| **Production** | https://smart-locker.yeng.click | landing + login |
| Production — Admin | https://admin.smart-locker.yeng.click | requires `ADMIN` |
| Production — Agent | https://agent.smart-locker.yeng.click | requires `AGENT` |
| Production — Customer | https://customer.smart-locker.yeng.click | requires `CUSTOMER` |

---

## Approach

The POC is a clean, well-factored FastAPI + React app: solid domain logic
(locker allocation, two-phase store/pickup, tiered charges, concurrency
handling) but **no authentication**, and all three operator views are served
from a single origin via client-side routing.

Rather than fork and rewrite it, I treated the POC as the **source of truth for
business logic** and layered production concerns on top as a thin **overlay**:

- The production Docker image clones the POC at build time (`Dockerfile`,
  `POC_REPO`/`POC_REF` build args) and copies a small set of overlay files over
  specific POC files.
- This keeps the two in sync: when the POC changes, rebuild and the production
  image picks up the new business logic while re-applying auth.

The overlay adds exactly three production concerns:

1. **Authentication** — JWT bearer tokens issued by `POST /api/auth/login`
   (OAuth2 password flow). Passwords hashed with bcrypt. Users stored in the DB
   and seeded on startup from environment config.
2. **Authorization** — role-based access control. Three roles map to the three
   views: `ADMIN`, `AGENT`, `CUSTOMER`. Each business router is gated by the
   role that owns it via a `require_role(...)` FastAPI dependency.
3. **Per-view subdomains** — each view is its own URL surface. The frontend
   selects which view to render from the request hostname and gates it behind
   login + a role check. **Security is enforced server-side on the API** — the
   view split is UX, not the security boundary.

### Role → capability matrix

| Endpoint group | ADMIN | AGENT | CUSTOMER |
|----------------|:-----:|:-----:|:--------:|
| `/api/lockers` (create/list) | ✅ | ❌ | ❌ |
| `/api/packages` (hold/complete/cancel) | ❌ | ✅ | ❌ |
| `/api/pickups` (open/close) | ❌ | ❌ | ✅ |
| `/api/notifications` (transaction log) | ✅ | ❌ | ❌ |
| `/api/sizes` (reference data) | ✅ | ✅ | ✅ |

This matrix is verified by an integration test (login as each role, assert the
allowed calls succeed and disallowed calls return `403`).

---

## Architecture

```
                         Internet (443)
                              │
                    ┌─────────────────────┐
                    │  Caddy (TLS term.)  │
                    │  *.yeng.click  +    │
                    │  *.smart-locker.…   │  ← 2 wildcard certs (Route 53)
                    └─────────────────────┘
                              │ reverse_proxy (by Host)
        ┌─────────────────────┼───────────────────────────┐
        ▼                     ▼                            ▼
  smart-locker.…      admin/agent/customer.          smart-locker-poc.…
  (landing/login)     smart-locker.…                 (POC, :8000)
        └──────────── 127.0.0.1:8100 ─────────────┘
                     production container
             (FastAPI API + built SPA, one image)
                              │
                        SQLite @ /data
```

All four production subdomains proxy to **one** container on `127.0.0.1:8100`.
The container serves the whole API plus the built SPA; the SPA reads the
hostname to decide which view to show. One image keeps the build, deploy, and
data story simple while still presenting four distinct app surfaces.

---

## Design decisions

- **Overlay over fork.** Cloning the POC at build time and overlaying auth files
  keeps business logic in one place and makes the production diff small and
  reviewable. The alternative (copying the whole codebase in) would drift.
- **Stateless JWT.** Access tokens are self-contained (subject + role + expiry),
  so the API needs no session store and scales horizontally. Trade-off:
  revocation is coarse (see trade-offs).
- **Authorization at the router boundary.** Applying `require_role(...)` as a
  router-level dependency (rather than per-endpoint) means every current and
  future endpoint in that router inherits the guard by default — safer as the
  API grows.
- **Server-side enforcement, client-side UX.** The frontend gate (login screen,
  "wrong role" screen) is purely for user experience. Every protected call is
  authorized on the server, so loading the agent bundle grants no agent powers.
- **One container, host-based views.** Simpler than four containers/images for
  the same code. The role guard, not the subdomain, is the security control.
- **Two wildcard certificates.** `*.yeng.click` does not cover third-level names
  like `admin.smart-locker.yeng.click`, so Caddy obtains a second wildcard,
  `*.smart-locker.yeng.click`, via the same Route 53 DNS-01 challenge.
- **Secrets from the environment.** `JWT_SECRET` has no insecure in-code default
  (the app refuses to start without it). Seed passwords are generated randomly
  by `deploy.sh` on first run and printed once.

---

## Assumptions

- The three roles (`ADMIN`, `AGENT`, `CUSTOMER`) are sufficient; there is no
  multi-tenant / per-site scoping yet — a locker bank is a single shared estate.
- Customers are given a **shared `CUSTOMER` operator login** plus a per-package
  pickup code (the POC's existing mechanism). Individual customer accounts are
  out of scope for this pass (see improvements).
- Bootstrap/seed accounts are acceptable for initial access; real user
  management (invite, reset, disable) can follow.
- SQLite is adequate for the current scale, inherited from the POC. The
  `DATABASE_URL` swap to Postgres is a config change, not a code change.
- The deployment target is a single EC2 host (no orchestrator), consistent with
  the rest of this workspace.

---

## Trade-offs considered

- **JWT vs server sessions.** Chose stateless JWT for simplicity and scale.
  Cost: no easy immediate revocation — a stolen token is valid until it expires.
  Mitigated with a short TTL (60 min default). A denylist or rotating refresh
  tokens would be the next step.
- **Token in `localStorage` vs httpOnly cookie.** `localStorage` is simple and
  works cleanly across the subdomains, but is exposed to XSS. An httpOnly,
  `Secure`, `SameSite` cookie scoped to `.smart-locker.yeng.click` would be more
  robust; it adds CSRF handling. Given the POC's small surface, I kept
  `localStorage` for this pass and documented the upgrade path.
- **One container vs one-per-view.** One container is simpler to build/operate
  and the security boundary is the API role check regardless. Separate
  containers would give independent scaling/isolation per view at higher
  operational cost — not justified yet.
- **Shared customer login vs per-customer accounts.** Kept the POC's pickup-code
  model to stay in scope; real customer identity is the biggest functional gap.
- **Overlay build vs vendoring the source.** The overlay depends on the POC repo
  being reachable at build time. Vendoring would remove that dependency but
  reintroduce drift. I favored freshness.

---

## What I'd improve with more time

- **Per-customer accounts** with self-service pickup (email/OTP), replacing the
  shared `CUSTOMER` login.
- **Refresh tokens + revocation** (short-lived access token, rotating refresh
  token, server-side denylist) and move tokens to httpOnly cookies.
- **Postgres + Alembic migrations** in place of SQLite for durability,
  concurrency, and backups; add connection pooling.
- **Audit + observability**: structured request logging with the acting user,
  metrics (Prometheus), and tracing; alerting on auth failures.
- **Rate limiting / lockout** on `/api/auth/login` to blunt brute force.
- **Automated tests in CI**: the auth integration test here plus the POC's own
  suite, run on every build; image vulnerability scanning.
- **Least-privilege per-view builds**: ship only each view's bundle to its
  subdomain so the admin JS is never served to customers (defense in depth).
- **Secrets manager** (AWS Secrets Manager / SSM) instead of an `.env` file.
- **CSP and stricter headers** tuned per view.

---

## Build & verification status

The production image has been built and exercised end-to-end locally:

- `docker build` from the POC source + overlay succeeds (final image ~198 MB).
- `docker compose config` validates the compose wiring.
- The running container passes live HTTP checks: `/api/health`, unauthenticated
  requests rejected (401), login per role, cross-role denial (agent creating a
  locker → 403), the full store → pickup happy path, and the SPA is served.

Not verifiable locally (needs the EC2 host + AWS): live ACME cert issuance and
real subdomain routing through Caddy.

## Deploy

Prerequisites: the Caddy stack (`../../caddy`) deployed, and DNS records for
`*.yeng.click` **and** `*.smart-locker.yeng.click` pointing at the host (the
`caddy/setup-dns.sh` script creates both).

```bash
sudo ./deploy.sh
```

On first run this generates `.env` with a random `JWT_SECRET` and random
passwords for `admin` / `agent` / `customer`, printed once — save them. It then
builds the image from the POC source + overlay and starts the container on
`127.0.0.1:8100`.

To rebuild after a POC change:

```bash
sudo docker compose build --no-cache && sudo docker compose up -d
```

## Configuration

See `.env.example`. Key variables:

| Var | Purpose |
|-----|---------|
| `JWT_SECRET` | **required** — HS256 signing secret (`openssl rand -hex 32`) |
| `ACCESS_TOKEN_TTL_MINUTES` | access-token lifetime (default 60) |
| `SEED_*_USERNAME` / `SEED_*_PASSWORD` | bootstrap accounts (seeded once) |
| `STORAGE_UNIT_RATE`, `HOLD_TIMEOUT_SECONDS` | POC business knobs |

## How the overlay maps to the POC

| Overlay file | Effect in the image |
|--------------|---------------------|
| `backend/app/auth.py` | new: JWT + bcrypt + `require_role` |
| `backend/app/seed.py` | new: idempotent user seeding |
| `backend/app/routers/auth_router.py` | new: `/api/auth/login`, `/api/auth/me` |
| `backend/app/config_prod.py` | replaces `app/config.py` (adds auth settings) |
| `backend/app/main_prod.py` | replaces `app/main.py` (mounts auth, gates routers) |
| `backend/app/models_user.py` | appended to `app/models.py` (adds `User` table) |
| `frontend/src/auth.ts` | new: login, token storage, `authFetch`, view detection |
| `frontend/src/Login.tsx` | new: login gate |
| `frontend/src/api_prod.ts` | replaces `src/api.ts` (routes calls through `authFetch`) |
| `frontend/src/main_prod.tsx` | replaces `src/main.tsx` (per-view + auth gate) |
| `backend/requirements-prod.txt` | adds PyJWT, passlib/bcrypt, python-multipart |
