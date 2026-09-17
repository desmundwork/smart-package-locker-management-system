"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers import lockers, notifications, packages, pickups, sizes


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Smart Package Locker Management System",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(lockers.router)
app.include_router(packages.router)
app.include_router(pickups.router)
app.include_router(notifications.router)
app.include_router(sizes.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


def mount_spa(app: FastAPI, static_dir: Path) -> bool:
    """Serve the built React SPA (design §1) from ``static_dir`` if present.

    In the container the frontend build is copied to backend/static. If it's
    absent (backend-only dev/test), the API still runs; only the UI is
    unavailable. Returns True if the SPA was mounted.
    """
    if not (static_dir / "index.html").exists():
        return False

    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Unmatched API routes must stay JSON 404s, not the SPA shell — otherwise
        # a client fetching a wrong /api path would get index.html with a 200.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Client-side routing fallback: any other non-API path returns index.html.
        candidate = static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")

    return True


# In the container the SPA build is copied to backend/static.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
mount_spa(app, _STATIC_DIR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)
