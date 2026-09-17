# Stage 1 — build the React SPA
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2 — Python runtime serving API + built SPA
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# Built SPA -> static dir that main.py serves.
COPY --from=frontend /frontend/dist ./static

# SQLite lives here. Declared as a volume so data survives container restarts
# (without a mounted volume the DB is still ephemeral — mount /data to persist).
# DATABASE_URL points the app at this directory.
ENV DATABASE_URL=sqlite:////data/locker.db
RUN mkdir -p /data

# Run as an unprivileged user. Own the app and data dirs so the process can
# write the SQLite file and create tables on startup.
RUN adduser --disabled-password --gecos "" --uid 10001 appuser \
    && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/api/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
