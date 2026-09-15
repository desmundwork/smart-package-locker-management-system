"""Storage charge tier boundary tests (unit) — requirements 6."""
from datetime import datetime, timedelta

from app.charges import billable_days, storage_charge


def _charge(hours: float, rate: float = 1.0) -> float:
    start = datetime(2026, 1, 1, 0, 0, 0)
    return storage_charge(start, start + timedelta(hours=hours), rate)


def test_zero_and_partial_day():
    assert _charge(0) == 0
    assert _charge(1) == 1   # partial day counts as day 1 at rate X
    assert _charge(24) == 1


def test_first_tier_five_days():
    assert _charge(24 * 5) == 5


def test_second_tier():
    # days 1-5 = 5X, days 6-10 = 10X -> 15X at day 10
    assert _charge(24 * 10) == 15


def test_third_tier():
    # + day 11 at 3X -> 18X
    assert _charge(24 * 11) == 18


def test_rate_scaling():
    assert _charge(24 * 11, rate=2) == 36


def test_billable_days_ceil():
    start = datetime(2026, 1, 1)
    assert billable_days(start, start + timedelta(hours=25)) == 2
