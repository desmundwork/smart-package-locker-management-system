# smart-locker-poc.yeng.click

Deployment for the [Smart Package Locker Management System](https://github.com/desmundwork/smart-package-locker-management-system)
**POC**, served as-is at **https://smart-locker-poc.yeng.click**.

This is the unmodified proof-of-concept (all views open, no auth). The
productionized version — with authentication, role-based authorization, and
per-view subdomains — lives in `../smart-locker-prod` and is served at
`smart-locker.yeng.click`.

## What this is

A FastAPI + React app packaged as a single Docker image published on GHCR.
It listens on port `8000` and stores a SQLite DB at `/data/locker.db`.

Views:
- `/admin` — manage lockers, locker map, transaction log
- `/agent` — store incoming parcels (mobile)
- `/customer` — pick up parcels with a code (mobile)
- `/docs` — OpenAPI docs

## How it's served

```
Internet ──TLS──> Caddy (443) ──proxy──> 127.0.0.1:8000 (Docker container)
   smart-locker-poc.yeng.click
```

The container is bound to `127.0.0.1:8000` (loopback), so it is only reachable
through Caddy, never directly from the internet. TLS is handled by the shared
`*.yeng.click` wildcard cert in `../../caddy`.

## Deploy (on EC2 Ubuntu)

```bash
sudo ./deploy.sh
```

This installs Docker (if missing), pulls the latest image, and starts it via
`docker-compose.yml` with a persistent `locker-data` volume.

Make sure the Caddy stack in `../../caddy` is deployed too — it provides the
`smart-locker.yeng.click` route and the TLS certificate.

## Update to the latest image

```bash
sudo ./deploy.sh   # re-pulls :latest and restarts
```

## Configuration

Environment variables are set in `docker-compose.yml`:

| Var | Default | Purpose |
|-----|---------|---------|
| `DATABASE_URL` | `sqlite:////data/locker.db` | DB connection (persisted on volume) |
| `STORAGE_UNIT_RATE` | `1` | tiered storage-charge rate |
| `HOLD_TIMEOUT_SECONDS` | `120` | auto-release unconfirmed holds |
| `PORT` | `8000` | HTTP port inside the container |

## Data persistence

The SQLite DB lives in the `locker-data` Docker volume. It survives container
restarts and image updates. To back it up:

```bash
docker run --rm -v locker-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/locker-data-backup.tgz -C /data .
```
