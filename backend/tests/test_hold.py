"""Smallest-fit hold (phase 1) — reserve the smallest fitting locker."""


def test_hold_picks_smallest_fit(client):
    for size in ["SMALL", "MEDIUM", "LARGE"]:
        client.post("/api/lockers", json={"size": size})
    hold = client.post("/api/packages/hold", json={"size": "SMALL"}).json()
    assert hold["held"] is True
    assert hold["locker_id"] == "S-001"
    assert len(hold["pickup_code"]) == 6
    # Locker is now HELD, not AVAILABLE.
    lockers = {l["id"]: l for l in client.get("/api/lockers").json()}
    assert lockers["S-001"]["status"] == "HELD"


def test_hold_uses_next_size_up_when_exact_absent(client):
    client.post("/api/lockers", json={"size": "MEDIUM"})
    client.post("/api/lockers", json={"size": "LARGE"})
    hold = client.post("/api/packages/hold", json={"size": "SMALL"}).json()
    assert hold["held"] is True
    assert hold["locker_id"] == "M-001"  # smallest fitting


def test_hold_fails_when_no_fit(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    hold = client.post("/api/packages/hold", json={"size": "LARGE"}).json()
    assert hold["held"] is False
    assert "no locker" in hold["message"].lower()


def test_hold_logs_attempt_and_success(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    client.post("/api/packages/hold", json={"size": "SMALL"})
    types = {n["event_type"] for n in client.get("/api/notifications").json()}
    assert "STORE_ATTEMPT" in types
    assert "HOLD_SUCCESS" in types
