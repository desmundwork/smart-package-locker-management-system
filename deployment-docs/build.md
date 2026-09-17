# Build

How to build the Smart Package Locker Management System image locally.

## Prerequisites

- Docker 24+ (`docker --version`)
- Git

The image is multi-stage: stage 1 builds the React SPA, stage 2 runs FastAPI serving the API and the built static assets. You do not need Node or Python installed locally — Docker handles both stages.

## Variables

Set these once so the commands below are copy-paste ready. Replace `OWNER` with your GitHub username or org (lowercase).

```bash
export OWNER=your-github-username
export IMAGE=ghcr.io/$OWNER/smart-package-locker
export TAG=0.1.0
```

## Build the image

From the repository root (where the `Dockerfile` lives):

```bash
docker build -t $IMAGE:$TAG -t $IMAGE:latest .
```

## Verify the build

```bash
docker images | grep smart-package-locker
```

Optionally run it locally before pushing (see `run.md`):

```bash
docker run --rm -p 8000:8000 $IMAGE:$TAG
# then open http://localhost:8000
```

## Notes

- The default database is SQLite inside the container. For a persistent or Postgres setup, see `run.md` (env vars `DATABASE_URL`, `STORAGE_UNIT_RATE`, `HOLD_TIMEOUT_SECONDS`, `PORT`).
- Rebuild with a new `TAG` for each release so images are immutable and traceable.
