"""Level 3 tiered charge, verified end-to-end through the pickup API.

Backdates a stored package's clock so the tiered rule is exercised against the
real /api/pickups/open response, not just the charge unit function.
"""
from datetime import timedelta

from sqlmodel import Session

import app.db as db  # read db.engine at call time (client fixture patches it)
from app.models import Package, now_utc


def _store(client, size="SMALL"):
    hold = client.post("/api/packages/hold", json={"size": size}).json()
    done = client.post("/api/packages/complete", json={"package_id": hold["package_id"]}).json()
    return done["locker_id"], done["pickup_code"], hold["package_id"]


def _backdate(package_id, hours):
    with Session(db.engine) as s:
        pkg = s.get(Package, package_id)
        pkg.stored_at = now_utc() - timedelta(hours=hours)
        s.add(pkg)
        s.commit()


def _pickup(client, locker_id, code):
    return client.post("/api/pickups/open", json={"locker_id": locker_id, "pickup_code": code}).json()


def test_pickup_returns_audit_fields(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code, _pid = _store(client)
    res = _pickup(client, locker_id, code)
    assert res["stored_at"] is not None
    assert res["retrieved_at"] is not None
    assert res["billable_days"] >= 1  # a just-stored package bills its first partial day


# Backdate to 1h short of the N-day mark so the live pickup time lands squarely
# in day N (ceil), avoiding a boundary race where real elapsed ms tips into N+1.
def test_first_tier_via_api(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code, pid = _store(client)
    _backdate(pid, hours=24 * 5 - 1)
    res = _pickup(client, locker_id, code)
    assert res["billable_days"] == 5
    assert res["storage_charge"] == 5


def test_second_tier_via_api(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code, pid = _store(client)
    _backdate(pid, hours=24 * 10 - 1)
    res = _pickup(client, locker_id, code)
    assert res["billable_days"] == 10
    assert res["storage_charge"] == 15


def test_third_tier_via_api(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code, pid = _store(client)
    _backdate(pid, hours=24 * 11 - 1)
    res = _pickup(client, locker_id, code)
    assert res["billable_days"] == 11
    assert res["storage_charge"] == 18


def test_partial_day_rounds_up_via_api(client):
    client.post("/api/lockers", json={"size": "SMALL"})
    locker_id, code, pid = _store(client)
    _backdate(pid, hours=25)
    res = _pickup(client, locker_id, code)
    assert res["billable_days"] == 2
    assert res["storage_charge"] == 2
