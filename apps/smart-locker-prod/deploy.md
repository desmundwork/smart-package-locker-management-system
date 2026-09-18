# Production deploy — GHCR image

The production Smart Package Locker image (auth + RBAC + per-view subdomains)
is a **separate** artifact from the POC. It builds from the POC source at build
time and overlays the production code (see `Dockerfile`).

| | POC | Production |
|-|-----|------------|
| Image | `ghcr.io/desmundwork/smart-package-locker-management-system` | `ghcr.io/desmundwork/smart-locker-prod` |
| Tags | `0.1.0`, `latest` | `1.0.0`, `latest` |
| Auth | none | JWT + RBAC |

## Variables

```bash
export IMAGE=ghcr.io/desmundwork/smart-locker-prod
export TAG=1.0.0
```

## 1. Build for Ubuntu (linux/amd64) and push to GHCR

GHCR push requires a **Personal Access Token (classic)** with the
`write:packages` scope. A normal `gh`/OAuth login is not sufficient to push
container packages.

```bash
# 1. Log in with a PAT that has write:packages
export CR_PAT=your-classic-PAT-with-write:packages
echo "$CR_PAT" | docker login ghcr.io -u desmundwork --password-stdin

# 2. Build for the Ubuntu target arch and push (one step)
docker buildx build --platform linux/amd64 \
  -t $IMAGE:$TAG -t $IMAGE:latest \
  --push .
```

> Build for `linux/arm64` too (e.g. Graviton EC2) by using
> `--platform linux/amd64,linux/arm64`.

### Make the package public (first release only)

New GHCR packages are private and there is no REST API to change container
visibility — do it in the web UI:

`https://github.com/users/desmundwork/packages/container/smart-locker-prod/settings`
→ Danger Zone → Change visibility → **Public**.

## 2. Run on the Ubuntu host

The production image expects auth config via environment (no insecure
defaults). Easiest path on the host is `apps/smart-locker-prod/deploy.sh`,
which generates `.env` (random `JWT_SECRET` + seed passwords, `REVIEW_MODE=true`
for the verification stage) and starts it via `docker-compose.yml`.

To run the published image directly instead:

```bash
docker run -d --name smart-locker-prod --restart unless-stopped \
  -p 127.0.0.1:8100:8000 \
  -v locker-prod-data:/data \
  -e DATABASE_URL="sqlite:////data/locker.db" \
  -e JWT_SECRET="$(openssl rand -hex 32)" \
  -e SEED_ADMIN_USERNAME=admin    -e SEED_ADMIN_PASSWORD="$(openssl rand -hex 8)" \
  -e SEED_AGENT_USERNAME=agent    -e SEED_AGENT_PASSWORD="$(openssl rand -hex 8)" \
  -e SEED_CUSTOMER_USERNAME=customer -e SEED_CUSTOMER_PASSWORD="$(openssl rand -hex 8)" \
  -e REVIEW_MODE=true \
  ghcr.io/desmundwork/smart-locker-prod:1.0.0
```

Bind to `127.0.0.1` so it's reachable only through Caddy (`../../caddy`), which
terminates TLS and routes `smart-locker.yeng.click` + the `admin/agent/customer`
subdomains to `:8100`.

## Build/push status

- Image built for `linux/amd64` and tagged `1.0.0` + `latest` locally (198 MB).
- Push pending: needs a PAT with `write:packages` (the interactive OAuth login
  available at build time lacked the push scope).
