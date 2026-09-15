"""Locker management (Admin) — create with per-size ids and list."""


def test_create_marks_available_and_returns_201(client):
    res = client.post("/api/lockers", json={"size": "SMALL"})
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == "S-001"
    assert body["size"] == "SMALL"
    assert body["status"] == "AVAILABLE"


def test_ids_increment_per_size(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    client.post("/api/lockers", json={"size": "MEDIUM"})
    client.post("/api/lockers", json={"size": "SMALL"})
    client.post("/api/lockers", json={"size": "LARGE"})
    ids = [l["id"] for l in client.get("/api/lockers").json()]
    assert ids == ["L-001", "M-001", "S-001", "S-002"]  # ordered by id


def test_unknown_size_rejected(client):
    assert client.post("/api/lockers", json={"size": "HUGE"}).status_code == 422


def test_list_empty(client):
    assert client.get("/api/lockers").json() == []
