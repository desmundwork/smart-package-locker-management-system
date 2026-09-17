# Build

How to build the Smart Package Locker Management System image locally.

## Prerequisites

- Docker 24+ (`docker --version`)
- Git

The image is multi-stage: stage 1 builds the React SPA, stage 2 runs FastAPI serving the API and the built static assets. You do not need Node or Python installed locally — Docker handles both stages.

## Variables

Set these once so the commands below are copy-paste ready. Replace `OWNER` with your GitHub username or org (lowercase).

```bash
export OWNER=desmundwork
export IMAGE=ghcr.io/$OWNER/smart-package-locker-management-system
export TAG=0.1.0
```

## Build for local testing (single architecture)

From the repository root (where the `Dockerfile` lives). This builds for your
machine's architecture and loads the image into the local Docker store so you
can run it immediately:

```bash
docker build -t $IMAGE:$TAG -t $IMAGE:latest .
docker images | grep smart-package-locker-management-system
docker run --rm -p 8000:8000 $IMAGE:$TAG   # then open http://localhost:8000
```

> **Architecture note.** `docker build` produces an image for the host CPU only.
> On an Apple Silicon Mac that is `linux/arm64`, which will **not** run on a
> typical `linux/amd64` Ubuntu server. For anything you deploy, build multi-arch
> (below) so it runs on both.

## Build multi-architecture and push (linux/amd64 + linux/arm64)

Ubuntu hosts are almost always `linux/amd64`, so the released image must include
that platform. Use `docker buildx`, which builds a multi-platform **manifest
list** and pushes it directly to the registry (a multi-arch image cannot be
loaded into the local single-arch docker store, so this builds and pushes in one
step).

### 1. One-time: create a buildx builder

`buildx` ships with modern Docker. Create (once) a builder that can emulate other
architectures via QEMU:

```bash
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

(If you have run this before, just select it: `docker buildx use multiarch`.)

### 2. Log in to the registry

```bash
echo "$CR_PAT" | docker login ghcr.io -u "$OWNER" --password-stdin
# or, with the GitHub CLI: gh auth token | docker login ghcr.io -u "$OWNER" --password-stdin
```

### 3. Build for both platforms and push

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t $IMAGE:$TAG -t $IMAGE:latest \
  --push .
```

### 4. Verify the published platforms

```bash
docker buildx imagetools inspect $IMAGE:$TAG
```

You should see entries for both `linux/amd64` and `linux/arm64`. When an Ubuntu
(amd64) host pulls the tag, Docker automatically selects the matching platform.

## Notes

- The default database is SQLite inside the container. For a persistent or Postgres setup, see `run.md` (env vars `DATABASE_URL`, `STORAGE_UNIT_RATE`, `HOLD_TIMEOUT_SECONDS`, `PORT`).
- Rebuild with a new `TAG` for each release so images are immutable and traceable.
- Multi-arch builds emulate the non-native platform (QEMU), so they are slower than a native single-arch build; that is expected.
