# =============================================================================
# Production image for the Smart Package Locker system.
#
# Strategy: start FROM the upstream POC source (cloned at build time), then
# overlay the production auth + per-view files. This keeps the POC as the
# single source of business logic and layers productionization on top, so the
# two stay in sync when the POC is updated (just rebuild).
#
# The overlay files live in this directory under backend/ and frontend/ and are
# copied into the cloned tree, replacing/extending specific POC files.
# =============================================================================

ARG POC_REPO=https://github.com/desmundwork/smart-package-locker-management-system.git
ARG POC_REF=main

# -----------------------------------------------------------------------------
# Stage 0 — fetch the POC source
# -----------------------------------------------------------------------------
FROM alpine/git AS source
ARG POC_REPO
ARG POC_REF
WORKDIR /src
RUN git clone --depth 1 --branch ${POC_REF} ${POC_REPO} repo

# -----------------------------------------------------------------------------
# Stage 1 — build the React SPA with the production entry (auth + per-view)
# -----------------------------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY --from=source /src/repo/frontend/ ./

# Overlay production frontend files.
COPY frontend/src/auth.ts ./src/auth.ts
COPY frontend/src/Login.tsx ./src/Login.tsx
COPY frontend/src/LandingProd.tsx ./src/LandingProd.tsx
COPY frontend/src/api_prod.ts ./src/api.ts
COPY frontend/src/main_prod.tsx ./src/main.tsx

RUN npm ci && npm run build

# -----------------------------------------------------------------------------
# Stage 2 — Python runtime serving API + built SPA, with auth
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# POC backend requirements + production auth requirements.
COPY --from=source /src/repo/backend/requirements.txt ./requirements.txt
COPY backend/requirements-prod.txt ./requirements-prod.txt
RUN pip install --no-cache-dir -r requirements.txt -r requirements-prod.txt

# POC backend source.
COPY --from=source /src/repo/backend/app ./app

# ---- Overlay production backend files ----
# New modules:
COPY backend/app/auth.py ./app/auth.py
COPY backend/app/seed.py ./app/seed.py
COPY backend/app/routers/auth_router.py ./app/routers/auth_router.py
# Replace config + main with production variants:
COPY backend/app/config_prod.py ./app/config.py
COPY backend/app/main_prod.py ./app/main.py
# Append the User model to the POC models module so init_db creates it.
COPY backend/app/models_user.py ./app/_models_user.py
RUN cat ./app/_models_user.py >> ./app/models.py && rm ./app/_models_user.py

# Built SPA -> static dir that main.py serves.
COPY --from=frontend /frontend/dist ./static

ENV DATABASE_URL=sqlite:////data/locker.db
RUN mkdir -p /data

RUN adduser --disabled-password --gecos "" --uid 10001 appuser \
    && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/api/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
