"""SPA fallback routing — the catch-all serves index.html for client routes but
must NOT shadow unmatched /api paths (those stay JSON 404s)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app_with_spa(tmp_path: Path) -> FastAPI:
    from app.main import mount_spa

    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>SPA</title>")
    (static / "assets" / "app.js").write_text("console.log('spa')")

    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    assert mount_spa(app, static) is True
    return app


def test_client_route_falls_back_to_index(tmp_path):
    client = TestClient(_app_with_spa(tmp_path))
    res = client.get("/admin")
    assert res.status_code == 200
    assert "SPA" in res.text


def test_static_asset_is_served(tmp_path):
    client = TestClient(_app_with_spa(tmp_path))
    res = client.get("/assets/app.js")
    assert res.status_code == 200
    assert "spa" in res.text


def test_known_api_route_still_works(tmp_path):
    client = TestClient(_app_with_spa(tmp_path))
    assert client.get("/api/health").json() == {"status": "ok"}


def test_unknown_api_route_is_json_404_not_spa(tmp_path):
    client = TestClient(_app_with_spa(tmp_path))
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    assert "SPA" not in res.text
