"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Smart Package Locker Management System",
    version="0.1.0",
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)
