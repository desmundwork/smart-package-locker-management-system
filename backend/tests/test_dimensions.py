"""Locker dimensions / volume spec exposed via the API and on each locker."""
from app.models import SIZE_ORDER, Size, dimensions_for


def test_volume_matches_dimensions():
    for size in SIZE_ORDER:
        d = dimensions_for(size)
        assert d.volume_litres == round(d.width_cm * d.depth_cm * d.height_cm / 1000, 1)


def test_dimensions_increase_with_size():
    vols = [dimensions_for(s).volume_litres for s in SIZE_ORDER]
    assert vols == sorted(vols)
    assert len(set(vols)) == len(vols)  # strictly distinct


def test_sizes_endpoint(client):
    specs = client.get("/api/sizes").json()
    assert [s["size"] for s in specs] == [s.value for s in SIZE_ORDER]
    for spec in specs:
        d = spec["dimensions"]
        assert d["width_cm"] > 0 and d["depth_cm"] > 0 and d["height_cm"] > 0
        assert d["volume_litres"] > 0
        assert spec["label"]


def test_locker_out_includes_dimensions(client):
    assert client.post("/api/lockers", json={"size": "MEDIUM"}).status_code == 201
    locker = client.get("/api/lockers").json()[0]
    assert "dimensions" in locker
    assert locker["dimensions"]["volume_litres"] == dimensions_for(Size.MEDIUM).volume_litres
