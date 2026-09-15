"""End-to-end API flow — requirements 1, 3, 5, 8, 10.

Store is two-step (hold -> complete); pickup is two-step (open -> close).
"""


def _store(client, size):
    """Full happy-path store: hold then complete. Returns (locker_id, code)."""
    hold = client.post("/api/packages/hold", json={"size": size}).json()
    assert hold["held"] is True
    done = client.post("/api/packages/complete", json={"package_id": hold["package_id"]}).json()
    assert done["stored"] is True
    return done["locker_id"], done["pickup_code"]


def test_smallest_fit_and_full_lifecycle(client):
    for size in ["SMALL", "MEDIUM", "LARGE"]:
        assert client.post("/api/lockers", json={"size": size}).status_code == 201

    lockers = client.get("/api/lockers").json()
    assert len(lockers) == 3
    assert all(l["status"] == "AVAILABLE" for l in lockers)

    # SMALL package takes the SMALL locker (smallest fit).
    locker_id, code = _store(client, "SMALL")
    assert locker_id == "S-001"

    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers["S-001"]["status"] == "OCCUPIED"

    # Retrieve — open then close.
    pick = client.post("/api/pickups/open", json={"locker_id": "S-001", "pickup_code": code}).json()
    assert pick["opened"] is True
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers["S-001"]["status"] == "OPEN"

    closed = client.post("/api/pickups/close", json={"locker_id": "S-001"}).json()
    assert closed["closed"] is True
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers["S-001"]["status"] == "AVAILABLE"

    # Reusing the code fails.
    assert client.post("/api/pickups/open", json={"locker_id": "S-001", "pickup_code": code}).json()["opened"] is False


def test_hold_then_cancel_frees_locker(client):
    client.post("/api/lockers", json={"size": "MEDIUM"})
    hold = client.post("/api/packages/hold", json={"size": "SMALL"}).json()
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers[hold["locker_id"]]["status"] == "HELD"
    client.post("/api/packages/cancel", json={"package_id": hold["package_id"]})
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers[hold["locker_id"]]["status"] == "AVAILABLE"


def test_no_suitable_locker(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    assert client.post("/api/packages/hold", json={"size": "LARGE"}).json()["held"] is False


def test_log_records_two_step_events(client):
    client.post("/api/lockers", json={"size": "MEDIUM"})
    _store(client, "SMALL")
    types = {n["event_type"] for n in client.get("/api/notifications").json()}
    assert {"STORE_ATTEMPT", "HOLD_SUCCESS", "STORE_SUCCESS", "CODE_SEND"} <= types
