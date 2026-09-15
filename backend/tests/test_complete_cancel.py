"""Two-phase store: complete (confirm) and cancel (release)."""


def _hold(client, size="SMALL"):
    return client.post("/api/packages/hold", json={"size": size}).json()


def test_complete_marks_occupied(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    hold = _hold(client)
    done = client.post("/api/packages/complete", json={"package_id": hold["package_id"]}).json()
    assert done["stored"] is True
    assert done["locker_id"] == "S-001"
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers["S-001"]["status"] == "OCCUPIED"
    types = {n["event_type"] for n in client.get("/api/notifications").json()}
    assert {"STORE_SUCCESS", "CODE_SEND"} <= types


def test_cancel_frees_locker(client):
    client.post("/api/lockers", json={"size": "MEDIUM"})
    hold = _hold(client)
    res = client.post("/api/packages/cancel", json={"package_id": hold["package_id"]}).json()
    assert res["cancelled"] is True
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers[hold["locker_id"]]["status"] == "AVAILABLE"


def test_complete_unknown_package_is_clean(client):
    res = client.post("/api/packages/complete", json={"package_id": "nope"}).json()
    assert res["stored"] is False
    assert "nothing to confirm" in res["message"].lower()


def test_cancel_unknown_package_is_clean(client):
    res = client.post("/api/packages/cancel", json={"package_id": "nope"}).json()
    assert res["cancelled"] is False


def test_cannot_complete_twice(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    hold = _hold(client)
    client.post("/api/packages/complete", json={"package_id": hold["package_id"]})
    second = client.post("/api/packages/complete", json={"package_id": hold["package_id"]}).json()
    assert second["stored"] is False
