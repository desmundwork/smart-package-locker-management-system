"""Storage charge calculation — requirements 6 (Level 3).

Tiered rule: X/day for days 1-5, 2X/day for days 6-10, 3X/day for day 11+.
A "day" is 24 hours from stored_at; any partial day counts as a full day
(ceil), matching "beyond a certain duration" tiering.
"""
import math
from datetime import datetime

from app.models import as_utc


def billable_days(stored_at: datetime, retrieved_at: datetime) -> int:
    seconds = (as_utc(retrieved_at) - as_utc(stored_at)).total_seconds()
    if seconds <= 0:
        return 0
    return math.ceil(seconds / 86400)


def storage_charge(stored_at: datetime, retrieved_at: datetime, unit_rate: float) -> float:
    days = billable_days(stored_at, retrieved_at)
    total = 0.0
    for day in range(1, days + 1):
        if day <= 5:
            multiplier = 1
        elif day <= 10:
            multiplier = 2
        else:
            multiplier = 3
        total += multiplier * unit_rate
    return total
