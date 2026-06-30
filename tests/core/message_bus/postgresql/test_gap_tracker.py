# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone, timedelta
from profed.core.message_bus.postgresql import subscriber
from profed.core.message_bus.postgresql.subscriber import GapTracker


def _old(rid):
    return rid, datetime.now(timezone.utc) - timedelta(seconds=10)


def test_count_received_is_none_without_accepted_gaps():
    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(*_old(1))

    assert tracker.count_received() is None


def test_count_received_reports_the_window_for_a_settled_gap():
    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(*_old(1))
    tracker.accept_gap(2, 2)
    tracker.received(*_old(3))

    assert tracker.count_received() == (2, 1, 3)


def test_count_received_is_idempotent():
    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(*_old(1))
    tracker.accept_gap(2, 2)
    tracker.received(*_old(3))

    assert tracker.count_received() == tracker.count_received()


def test_count_received_is_none_while_rows_are_fresh():
    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(1, datetime.now(timezone.utc))
    tracker.accept_gap(2, 2)
    tracker.received(3, datetime.now(timezone.utc))

    assert tracker.count_received() is None


def test_count_received_window_covers_a_large_jump():
    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(*_old(1))
    tracker.received(*_old(2))
    tracker.accept_gap(3, 3)
    for rid in (4, 5, 6, 7, 8):
        tracker.received(*_old(rid))

    assert tracker.count_received() == (7, 1, 8)


def test_commit_prunes_a_settled_gap():
    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(*_old(1))
    tracker.accept_gap(2, 2)
    for rid in (3, 4, 5):
        tracker.received(*_old(rid))
    tracker.count_received()
    tracker.commit()

    assert tracker.count_received() is None


def test_gap_settles_after_the_timeout(monkeypatch):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = {"now": t0}
    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock["now"]
    monkeypatch.setattr(subscriber, "datetime", _Clock)

    tracker = GapTracker(0, timedelta(seconds=2))
    tracker.received(1, t0)
    tracker.accept_gap(2, 2)
    tracker.received(3, t0)

    assert tracker.count_received() is None
    clock["now"] = t0 + timedelta(seconds=3)
    assert tracker.count_received() == (2, 1, 3)

