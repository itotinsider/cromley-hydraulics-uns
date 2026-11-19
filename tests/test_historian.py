"""The SCADA historian (scada/historian.py): exception reporting, the stale gap, trends that hold a value."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scada"))
from historian import Historian  # noqa: E402


@pytest.fixture
def hist(tmp_path):
    return Historian(str(tmp_path / "h.db"), {"A": ("m", "a", 100.0), "B": ("", "b", 1.0)},
                     deadband_pct=1.0, max_interval_s=60.0, retention_days=1.0)


def samples(h, p):
    return h._db().execute("SELECT ts, value, quality FROM samples WHERE point_id = ? ORDER BY ts", (h.ids[p],)).fetchall()


def test_deadband_heartbeat_and_stale_gap(hist):
    t0 = 1_000_000.0
    for i in range(30):                                  # moves 0.5 < deadband 1.0 (1 % of 100): stored once
        hist.store(t0 + i, {"A": (t0 + i, 10.0 + (0.5 if i % 2 else 0.0))})
    assert len(samples(hist, "A")) == 1
    hist.store(t0 + 30, {"A": (t0 + 30, 12.0)})          # beyond the deadband
    hist.store(t0 + 95, {"A": (t0 + 95, 12.0)})          # unchanged, but the heartbeat is due
    assert [r[1] for r in samples(hist, "A")] == [10.0, 12.0, 12.0]
    hist.store(t0 + 96, {"A": (t0 + 96, None)})          # stale: one BAD row, no value
    hist.store(t0 + 97, {"A": (t0 + 97, None)})
    rows = samples(hist, "A")
    assert rows[-1][1:] == (None, 1) and len(rows) == 4


def test_trend_holds_values_and_shows_gaps(hist):
    t0 = 2_000_000.0
    hist.store(t0, {"A": (t0, 50.0)})
    hist.store(t0 + 50, {"A": (t0 + 50, 60.0)})
    hist.store(t0 + 100, {"A": (t0 + 100, None)})       # stale from here
    tr = hist.trend(["A"], minutes=3, points=18, end=t0 + 170)
    vals = dict(zip(tr["t"], tr["series"]["A"]))
    held = [v for t, v in vals.items() if t0 + 10 < t < t0 + 45]
    assert held and all(v == 50.0 for v in held)          # no samples: the last value holds
    assert all(v is None for t, v in vals.items() if t > t0 + 110)   # BAD: a gap, not a flat line


def test_events_and_soe(hist):
    hist.store(3_000_000.0, {}, events=[{"t": 3_000_000.0, "timestamp": "x", "kind": "operator", "source": "SCADA", "text": "hello"}],
               soe=[{"t": 3_000_000.0, "timestamp": "x", "unit": "Unit1", "kind": "trip", "code": "TRIP_X", "text": "t", "first_out": True}])
    assert hist.events(5)[0]["text"] == "hello"
    assert hist.soe(5)[0]["first_out"] is True
