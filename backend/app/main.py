"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import init_db
from app.routers import notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Smart Package Locker Management System",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(notifications.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)
