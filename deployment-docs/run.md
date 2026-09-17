# Run

How to run the container, locally or after pulling from a registry.

## Variables

```bash
export OWNER=your-github-username
export IMAGE=ghcr.io/$OWNER/smart-package-locker
export TAG=0.1.0
```

## Run (ephemeral, SQLite in container)

```bash
docker run --rm -p 8000:8000 $IMAGE:$TAG
```

Open:

- Landing / links: http://localhost:8000/
- Master system view (desktop): http://localhost:8000/admin
- Delivery agent view (mobile): http://localhost:8000/agent
- Customer view (mobile): http://localhost:8000/customer
- API docs (OpenAPI): http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## Run (persistent SQLite)

Mount a volume so the database survives container restarts:

```bash
docker run -d --name locker \
  -p 8000:8000 \
  -v locker-data:/data \
  -e DATABASE_URL="sqlite:////data/locker.db" \
  $IMAGE:$TAG
```

## Configuration (environment variables)

| Env var | Default | Meaning |
|---------|---------|---------|
| `DATABASE_URL` | `sqlite:///./locker.db` (Docker image sets `sqlite:////data/locker.db`) | DB connection string (swap to Postgres later) |
| `STORAGE_UNIT_RATE` | `1` | X in the tiered storage-charge rule |
| `HOLD_TIMEOUT_SECONDS` | `120` | Unconfirmed agent holds older than this are auto-released (0 disables) |
| `PORT` | `8000` | HTTP port inside the container |

Example with a custom rate and port:

```bash
docker run --rm -p 9000:9000 \
  -e PORT=9000 -e STORAGE_UNIT_RATE=5 \
  $IMAGE:$TAG
```

## Smoke test

```bash
# create a locker
curl -s -X POST localhost:8000/api/lockers -H 'content-type: application/json' -d '{"size":"MEDIUM"}'
# reserve one (agent, phase 1)
curl -s -X POST localhost:8000/api/packages/hold -H 'content-type: application/json' -d '{"size":"SMALL"}'
# view transaction log (admin)
curl -s localhost:8000/api/notifications
```

## Manage the container

```bash
docker logs -f locker      # tail logs
docker stop locker         # stop
docker rm locker           # remove
```
