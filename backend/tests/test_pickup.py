"""Two-phase pickup: open (validate + unlock) then close (free the locker)."""


def _store(client, size="SMALL"):
    hold = client.post("/api/packages/hold", json={"size": size}).json()
    done = client.post("/api/packages/complete", json={"package_id": hold["package_id"]}).json()
    return done["locker_id"], done["pickup_code"]


def test_open_then_close_frees_locker(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code = _store(client)

    opened = client.post("/api/pickups/open", json={"locker_id": locker_id, "pickup_code": code}).json()
    assert opened["opened"] is True
    # OPEN, not yet reusable.
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers[locker_id]["status"] == "OPEN"

    closed = client.post("/api/pickups/close", json={"locker_id": locker_id}).json()
    assert closed["closed"] is True
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers[locker_id]["status"] == "AVAILABLE"


def test_invalid_code_rejected(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, _code = _store(client)
    res = client.post("/api/pickups/open", json={"locker_id": locker_id, "pickup_code": "ZZZZZZ"}).json()
    assert res["opened"] is False


def test_reused_code_rejected(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code = _store(client)
    client.post("/api/pickups/open", json={"locker_id": locker_id, "pickup_code": code})
    client.post("/api/pickups/close", json={"locker_id": locker_id})
    again = client.post("/api/pickups/open", json={"locker_id": locker_id, "pickup_code": code}).json()
    assert again["opened"] is False


def test_close_non_open_locker_rejected(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    assert client.post("/api/pickups/close", json={"locker_id": "S-001"}).json()["closed"] is False


def test_unknown_locker_pickup_rejected(client):
    assert client.post("/api/pickups/open", json={"locker_id": "X-999", "pickup_code": "ABCDEF"}).json()["opened"] is False
