# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from datetime import datetime, timedelta, timezone

from unittest.mock import AsyncMock, MagicMock, patch
from profed.components.activity_resolver import fetcher
from profed.components.activity_resolver import storage as storage_module
from profed.components.activity_resolver.fetcher import (_backoff,
                                                         _backfeed,
                                                         _claim,
                                                         _decide,
                                                         _emit,
                                                         _fetch,
                                                         _object_version,
                                                         _resolution_id,
                                                         _tombstone_version,
                                                         _transition,
                                                         LEASE)

NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
OLD = datetime(2026, 1, 1, tzinfo=timezone.utc)
NEW = datetime(2026, 2, 1, tzinfo=timezone.utc)


def _row(state, version=None, cache_end=None, attempt=0, emitted_at=NOW, not_found_count=0):
    return {"state": state,
            "version": version,
            "cache_end": cache_end,
            "attempt": attempt,
            "emitted_at": emitted_at,
            "not_found_count": not_found_count}


def _responds(status, is_success, body=None, unparseable=False, headers=None):
    response = MagicMock()
    response.status_code = status
    response.is_success = is_success
    response.headers = headers or {}
    response.json = (MagicMock(side_effect=ValueError("no json"))
                     if unparseable else MagicMock(return_value=body))
    get = AsyncMock(return_value=response)
    return patch.object(fetcher, "HttpClient", return_value=MagicMock(get=get))


def _raises(error):
    return patch.object(fetcher, "HttpClient", return_value=MagicMock(get=AsyncMock(side_effect=error)))


@pytest.fixture(autouse=True)
def reset_registry():
    fetcher._config = {}
    fetcher._queues = {}
    fetcher._tasks = {}
    fetcher._started = False
    backup = storage_module._instance
    yield
    storage_module._instance = backup
    fetcher._queues = {}
    fetcher._tasks = {}
    fetcher._started = False


def test_backoff_starts_at_five_minutes_and_doubles():
    assert _backoff(1) == 300
    assert _backoff(2) == 600
    assert _backoff(3) == 1200


def test_backoff_is_capped_at_a_day():
    assert _backoff(10) == 86400
    assert _backoff(11) == 86400


def test_no_row_claims_the_first_attempt():
    assert _decide(None, OLD, NOW) == ("claim", 1)


def test_a_known_fresh_enough_version_is_skipped():
    assert _decide(_row("succeeded", version=NEW), OLD, NOW) == ("skip", None)


def test_a_newer_reference_claims_afresh():
    assert _decide(_row("succeeded", version=OLD, attempt=0), NEW, NOW) == ("claim", 1)


def test_a_fresh_attempting_makes_the_reference_wait():
    row = _row("attempting", attempt=1, emitted_at=NOW - timedelta(seconds=LEASE / 2))

    assert _decide(row, NEW, NOW) == ("wait", None)


def test_a_stale_attempting_is_reclaimed():
    row = _row("attempting", attempt=1, emitted_at=NOW - timedelta(seconds=LEASE * 2))

    assert _decide(row, NEW, NOW) == ("claim", 2)


def test_a_failed_within_backoff_waits():
    row = _row("failed", attempt=2, emitted_at=NOW - timedelta(seconds=60))

    assert _decide(row, NEW, NOW) == ("wait", None)


def test_a_failed_past_backoff_retries():
    row = _row("failed", attempt=2, emitted_at=NOW - timedelta(seconds=3600))

    assert _decide(row, NEW, NOW) == ("claim", 3)


def test_a_not_found_past_backoff_retries():
    row = _row("not_found", attempt=3, emitted_at=NOW - timedelta(seconds=86400))

    assert _decide(row, NEW, NOW) == ("claim", 4)


def test_a_fresh_tombstone_suppresses_the_fetch():
    future = NOW + timedelta(days=4)

    assert _decide(_row("tombstone", version=future), NEW, NOW) == ("skip", None)


def test_a_tombstone_past_grace_is_reattempted():
    past = NOW - timedelta(days=1)

    assert _decide(_row("tombstone", version=past, attempt=0), NOW, NOW) == ("claim", 1)


def test_a_url_reference_skips_a_freshly_cached_object():
    row = _row("succeeded", version=OLD, cache_end=NOW + timedelta(hours=1))

    assert _decide(row, None, NOW) == ("skip", None)


def test_a_url_reference_reverifies_an_expired_cache():
    row = _row("succeeded", version=OLD, cache_end=NOW - timedelta(hours=1), attempt=0)

    assert _decide(row, None, NOW) == ("claim", 1)


def test_a_url_reference_without_a_cache_claims():
    row = _row("succeeded", version=OLD, cache_end=None, attempt=0)

    assert _decide(row, None, NOW) == ("claim", 1)


def test_a_url_reference_skips_a_tombstone_in_grace():
    row = _row("tombstone", version=NOW + timedelta(days=4))

    assert _decide(row, None, NOW) == ("skip", None)


def test_a_url_reference_reattempts_a_tombstone_past_grace():
    row = _row("tombstone", version=NOW - timedelta(days=1), attempt=0)

    assert _decide(row, None, NOW) == ("claim", 1)


async def test_a_real_object_classifies_as_succeeded():
    obj = {"id": "https://r/1", "type": "Note", "content": "hi"}
    with _responds(200, True, obj):
        assert await _fetch("https://r/1") == ("succeeded", obj, None)


async def test_an_ap_tombstone_classifies_as_tombstone():
    obj = {"id": "https://r/1", "type": "Tombstone"}
    with _responds(200, True, obj):
        assert await _fetch("https://r/1") == ("tombstone", obj, None)


async def test_a_404_classifies_as_not_found():
    with _responds(404, False):
        assert await _fetch("https://r/1") == ("not_found", None, None)


async def test_a_410_classifies_as_tombstone():
    with _responds(410, False):
        assert await _fetch("https://r/1") == ("tombstone", None, None)


async def test_a_host_mismatch_between_id_and_url_is_a_failure():
    with _responds(200, True, {"id": "https://evil.example/1", "type": "Note"}):
        assert await _fetch("https://r/1") == ("failed", None, None)


async def test_a_500_classifies_as_failed():
    with _responds(503, False):
        assert await _fetch("https://r/1") == ("failed", None, None)


async def test_a_network_error_classifies_as_failed():
    with _raises(Exception("boom")):
        assert await _fetch("https://r/1") == ("failed", None, None)


async def test_an_unparseable_body_classifies_as_failed():
    with _responds(200, True, unparseable=True):
        assert await _fetch("https://r/1") == ("failed", None, None)


async def test_the_cache_control_max_age_is_read_on_success():
    obj = {"id": "https://r/1", "type": "Note"}

    with _responds(200, True, obj, headers={"Cache-Control": "public, max-age=600"}):
        assert await _fetch("https://r/1") == ("succeeded", obj, 600)


def test_object_version_prefers_updated_then_published():
    assert _object_version({"updated": "2026-02-01T00:00:00Z",
                            "published": "2026-01-01T00:00:00Z"}) == "2026-02-01T00:00:00Z"
    assert _object_version({"published": "2026-01-01T00:00:00Z"}) == "2026-01-01T00:00:00Z"
    assert _object_version({"content": "hi"}) is None


def test_a_succeeded_takes_the_objects_own_version_and_resets_counters():
    obj = {"id": "https://r/1", "type": "Note", "updated": "2026-02-01T00:00:00Z"}

    assert _transition("succeeded", obj, 3, 5, "2026-03-01T00:00:00Z", NOW, None) == \
        ("succeeded", "2026-02-01T00:00:00Z", (NOW + timedelta(seconds=3600)).isoformat(), 0, 0)


def test_a_succeeded_without_object_version_inherits_the_event_timestamp():
    obj = {"id": "https://r/1", "type": "Note", "content": "hi"}

    assert _transition("succeeded", obj, 3, 5, "2026-03-01T00:00:00Z", NOW, None) == \
        ("succeeded", "2026-03-01T00:00:00Z", (NOW + timedelta(seconds=3600)).isoformat(), 0, 0)


def test_an_ap_tombstone_buries_immediately():
    result = _transition("tombstone", {"type": "Tombstone"}, 1, 0, "2026-03-01T00:00:00Z", NOW, None)

    assert result == ("tombstone", (NOW + timedelta(days=4)).isoformat(), None, 0, 0)


def test_a_single_404_stays_a_retryable_not_found():
    assert _transition("not_found", None, 2, 0, "2026-03-01T00:00:00Z", NOW, None) == \
        ("not_found", None, None, 2, 1)


def test_a_404_crossing_the_threshold_becomes_a_tombstone():
    result = _transition("not_found", None, 9, 8, "2026-03-01T00:00:00Z", NOW, None)

    assert result == ("tombstone", (NOW + timedelta(days=4)).isoformat(), None, 0, 0)


def test_a_failed_keeps_the_not_found_count():
    assert _transition("failed", None, 4, 3, "2026-03-01T00:00:00Z", NOW, None) == \
        ("failed", None, None, 4, 3)


def test_a_succeeded_uses_the_max_age_for_cache_end():
    obj = {"id": "https://r/1", "type": "Note", "updated": "2026-02-01T00:00:00Z"}
    _, _, cache_end, _, _ = _transition("succeeded", obj, 1, 0, "2026-03-01T00:00:00Z", NOW, 600)

    assert cache_end == (NOW + timedelta(seconds=600)).isoformat()


def test_tombstone_version_is_now_plus_grace():
    assert _tombstone_version(NOW) == (NOW + timedelta(days=4)).isoformat()


def test_resolution_id_is_deterministic_per_object_sequence_attempt_state():
    first = _resolution_id("https://r/1", 42, 1, "attempting")
    assert first == _resolution_id("https://r/1", 42, 1, "attempting")
    assert first != _resolution_id("https://r/1", 42, 2, "attempting")
    assert first != _resolution_id("https://r/1", 43, 1, "attempting")
    assert first != _resolution_id("https://r/1", 42, 1, "succeeded")


async def test_emit_publishes_the_state_with_its_counters(fake_bus):
    await _emit("succeeded", "https://r/1", "https://r/boost/1", 1, "2026-02-01T00:00:00Z", 0, "2026-02-01T01:00:00Z")
    published = fake_bus.topic("resolution").published
    assert published[0]["event_type"] == "succeeded"
    assert published[0]["object_id"] == "https://r/1"
    assert published[0]["payload"] == {"object_id": "https://r/1",
                                       "version": "2026-02-01T00:00:00Z",
                                       "cache_end": "2026-02-01T01:00:00Z",
                                       "attempt": 1,
                                       "not_found_count": 0}


async def test_claim_wins_then_loses_on_the_same_object_referrer_and_attempt(fake_bus):
    assert await _claim("https://r/1", "https://r/boost/1", 1, 0) is True
    assert fake_bus.topic("resolution").published[0]["event_type"] == "attempting"
    assert await _claim("https://r/1", "https://r/boost/1", 1, 0) is False


async def test_a_new_attempt_can_still_claim_after_a_lost_one(fake_bus):
    assert await _claim("https://r/1", "https://r/boost/1", 1, 0) is True
    assert await _claim("https://r/1", "https://r/boost/1", 2, 0) is True


async def test_backfeed_publishes_an_ownerless_update(fake_bus):
    obj = {"id": "https://r/1", "type": "Note", "attributedTo": "https://r/bob", "content": "hi"}
    await _backfeed(obj, "2026-02-01T00:00:00Z")
    published = fake_bus.topic("incoming_activities").published
    assert published[0]["event_type"] == "Update"
    assert published[0]["payload"] == {"username": "", "activity": {"actor": "https://r/bob", "object": obj}}


async def test_backfeed_is_idempotent_per_object_and_version(fake_bus):
    obj = {"id": "https://r/1", "type": "Note", "content": "hi"}
    await _backfeed(obj, "2026-02-01T00:00:00Z")
    await _backfeed(obj, "2026-02-01T00:00:00Z")
    assert len(fake_bus.topic("incoming_activities").published) == 1


def test_ensure_task_is_a_noop_before_start():
    fetcher.ensure_task("https://r/1")
    assert "https://r/1" not in fetcher._tasks


def test_enqueue_queues_the_reference(monkeypatch):
    monkeypatch.setattr(fetcher, "ensure_task", lambda object_id: None)
    fetcher.enqueue("https://r/1", "https://r/boost/1", None, "2026-03-01T00:00:00Z", None)
    assert fetcher._queues["https://r/1"].get_nowait() == ("https://r/boost/1", None, "2026-03-01T00:00:00Z", None)


async def test_run_resolves_a_reference_backfeeds_then_exits(fake_bus, monkeypatch):
    succeeded = _row("succeeded", version=NEW, cache_end=NOW + timedelta(hours=1))

    class FakeStorage:
        def __init__(self, *rows):
            self.rows = list(rows)
        async def get(self, object_id):
            return self.rows.pop(0) if len(self.rows) > 1 else self.rows[-1]

    storage_module._instance = FakeStorage(None, succeeded)
    monkeypatch.setattr(fetcher, "_sleep", AsyncMock())
    monkeypatch.setattr(fetcher, "_fetch", AsyncMock(return_value=("succeeded", {"id": "https://r/1"}, None)))
    fetcher._queues["https://r/1"] = asyncio.Queue()
    fetcher._queues["https://r/1"].put_nowait(fetcher.Reference("https://r/boost/1", OLD, "2026-03-01T00:00:00Z", None))

    await fetcher._run("https://r/1")

    types = [p["event_type"] for p in fake_bus.topic("resolution").published]
    assert "attempting" in types
    assert "succeeded" in types
    assert fake_bus.topic("incoming_activities").published[0]["event_type"] == "Update"

