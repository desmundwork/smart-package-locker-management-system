"""Production FastAPI entrypoint.

Replaces the POC's app/main.py in the production image. Differences from POC:

1. Authentication router mounted at /api/auth (login, me).
2. Role-based authorization applied to the existing business routers:
     - lockers  : ADMIN only (create/list lockers)
     - packages : AGENT only (hold/complete/cancel a store)
     - pickups  : CUSTOMER only (open/close for pickup)
     - sizes    : any authenticated user (shared catalogue)
     - notifications : ADMIN only (full transaction log)
3. Per-view SPA serving: the VIEW env var selects which operator view this
   instance serves, so each subdomain (admin/agent/customer) is its own app
   surface even though they share one image + API.
4. Users are seeded on startup.

Authorization is enforced server-side on the API — the per-view frontend split
is a UX boundary, NOT the security boundary. Even if someone loads the agent
UI, the API rejects calls their role isn't allowed to make.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import Role, require_role
from app.config import settings
from app.db import init_db
from app.routers import auth_router, lockers, notifications, packages, pickups, sizes
from app.seed import seed_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_users()
    yield


app = FastAPI(
    title="Smart Package Locker Management System (Production)",
    version="1.0.0",
    lifespan=lifespan,
)

# ---- Public auth endpoints (no guard; login issues the token) ----
app.include_router(auth_router.router)

# ---- Business routers, each gated by the role that owns that surface ----
app.include_router(lockers.router, dependencies=[Depends(require_role(Role.ADMIN))])
app.include_router(packages.router, dependencies=[Depends(require_role(Role.AGENT))])
app.include_router(pickups.router, dependencies=[Depends(require_role(Role.CUSTOMER))])
app.include_router(notifications.router, dependencies=[Depends(require_role(Role.ADMIN))])
# Sizes catalogue is shared read-only reference data; any authenticated role.
app.include_router(
    sizes.router,
    dependencies=[Depends(require_role(Role.ADMIN, Role.AGENT, Role.CUSTOMER))],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version, "view": settings.view}


def mount_spa(app: FastAPI, static_dir: Path) -> bool:
    """Serve the built React SPA, forcing the client into the view configured
    for this instance via a bootstrap global the frontend reads."""
    if not (static_dir / "index.html").exists():
        return False

    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")

    return True


_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
mount_spa(app, _STATIC_DIR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)
