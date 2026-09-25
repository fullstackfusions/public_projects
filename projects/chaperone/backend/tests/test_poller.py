"""The reconcile rotation covers every region within RECONCILE_SLICES runs."""

import os

os.environ.setdefault("TABLE_NAME", "test")
from handlers import poller  # noqa: E402

REGIONS = [f"r{i:02d}" for i in range(17)]


def test_every_region_is_reconciled_once_per_cycle():
    seen = [r for minute in range(5) for r in poller.regions_for(minute, REGIONS, 5)]
    assert sorted(seen) == sorted(REGIONS)
    assert max(len(poller.regions_for(m, REGIONS, 5)) for m in range(5)) <= 4


def test_rotation_repeats():
    assert poller.regions_for(3, REGIONS, 5) == poller.regions_for(58, REGIONS, 5)
