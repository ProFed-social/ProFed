# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock
from profed.components.delivery_distributor import sender
from profed.components.delivery_distributor import storage as storage_module


NOW = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)


def _head(**kw):
    base = {"activity_id": "https://x/1", "seq": 5, "username": "alice",
            "activity": {"id": "https://x/1", "type": "Create",
                         "actor": "https://ex/actors/alice"},
            "attempt": 0, "attempt_at": None, "failed_at": None, "first_attempt_at": None}
    base.update(kw)
    return base


@pytest.fixture(autouse=True)
def reset_sender():
    sender._config = {}
    sender._started = False
    sender._registry = {}
    sender._inbox_cache = {}
    yield
    sender._registry = {}


def test_decide_never_attempted_claims_one():
    assert sender._decide(_head(attempt=0), NOW) == ("claim", 1)


def test_decide_in_flight_fresh_waits():
    assert sender._decide(_head(attempt=1, attempt_at=NOW - timedelta(seconds=10)), NOW) == ("wait",)


def test_decide_in_flight_stale_claims_next():
    assert sender._decide(_head(attempt=1, attempt_at=NOW - timedelta(seconds=200)), NOW) == ("claim", 2)


def test_decide_failed_before_backoff_waits():
    h = _head(attempt=1, attempt_at=NOW - timedelta(seconds=400), failed_at=NOW - timedelta(seconds=10))
    assert sender._decide(h, NOW) == ("wait",)


def test_decide_failed_after_backoff_claims_next():
    h = _head(attempt=1, attempt_at=NOW - timedelta(seconds=400), failed_at=NOW - timedelta(seconds=400))
    assert sender._decide(h, NOW) == ("claim", 2)


def test_decide_gives_up_after_max_total():
    h = _head(attempt=3, first_attempt_at=NOW - timedelta(seconds=200000),
              failed_at=NOW - timedelta(seconds=1))
    assert sender._decide(h, NOW) == ("give_up", 3)


@pytest.mark.asyncio
async def test_claim_wins_then_loses_on_same_message_id(fake_bus):
    assert await sender._claim("https://x/1", "bob@r", 1) is True
    assert fake_bus.topic("deliveries").published[0]["event_type"] == "attempting"
    assert await sender._claim("https://x/1", "bob@r", 1) is False


@pytest.mark.asyncio
async def test_deliver_success(monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=None))
    monkeypatch.setattr(sender, "_fetch_inbox_url", AsyncMock(return_value="https://r/inbox"))
    monkeypatch.setattr(sender, "_post_to_inbox", AsyncMock(return_value=Mock(status_code=202)))
    assert await sender._deliver(_head(), "bob@r") is True


@pytest.mark.asyncio
async def test_deliver_without_inbox_fails(monkeypatch):
    monkeypatch.setattr(sender, "_fetch_inbox_url", AsyncMock(return_value=None))
    assert await sender._deliver(_head(), "bob@r") is False


def test_ensure_task_noop_before_start():
    sender.ensure_task("bob@r")
    assert "bob@r" not in sender._registry


@pytest.mark.asyncio
async def test_run_delivers_dequeues_then_exits(fake_bus, monkeypatch):
    class FS:
        def __init__(self):
            self.open = [_head(activity_id="https://x/1", seq=5)]

        async def head(self, recipient):
            return sorted(self.open, key=lambda d: d["seq"])[0] if self.open else None

        async def dequeue(self, recipient, activity_id):
            self.open = [d for d in self.open if d["activity_id"] != activity_id]

    fs = FS()
    storage_module._instance = fs
    monkeypatch.setattr(sender, "_sleep", AsyncMock())
    monkeypatch.setattr(sender, "_deliver", AsyncMock(return_value=True))

    await sender._run("bob@r")

    types = [p["event_type"] for p in fake_bus.topic("deliveries").published]
    assert "attempting" in types and "done" in types
    assert fs.open == []


@pytest.mark.asyncio
async def test_the_recipient_url_is_asked_for_its_inbox(monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=None))
    fetch = AsyncMock(return_value="https://r/actors/bob/inbox")
    monkeypatch.setattr(sender, "_fetch_inbox_url", fetch)
    monkeypatch.setattr(sender, "_post_to_inbox", AsyncMock(return_value=Mock(status_code=202)))

    await sender._deliver(_head(), "https://r/actors/bob")

    fetch.assert_awaited_once_with("https://r/actors/bob")


LOCAL_HEAD = _head(activity_id="https://example.com/follows/1",
                   activity={"id": "https://example.com/follows/1",
                             "type": "Follow",
                             "username": "bob",
                             "actor": "https://example.com/actors/bob",
                             "object": "https://example.com/actors/alice"})


def _no_http(monkeypatch):
    fetch = AsyncMock()
    post = AsyncMock()
    monkeypatch.setattr(sender, "_fetch_inbox_url", fetch)
    monkeypatch.setattr(sender, "_post_to_inbox", post)
    return fetch, post


@pytest.mark.asyncio
async def test_a_local_user_is_delivered_to_without_http(fake_bus, monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=("public", "private")))
    fetch, post = _no_http(monkeypatch)

    assert await sender._deliver(LOCAL_HEAD, "https://example.com/actors/alice") is True
    fetch.assert_not_awaited()
    post.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_local_delivery_goes_to_the_recipient(fake_bus, monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=("public", "private")))
    _no_http(monkeypatch)

    await sender._deliver(LOCAL_HEAD, "https://example.com/actors/alice")

    published = fake_bus.topic("local_delivery").published
    assert [(p["event_type"], p["object_id"], p["payload"]["username"]) for p in published] == \
           [("Follow", "https://example.com/follows/1", "alice")]


@pytest.mark.asyncio
async def test_a_local_delivery_carries_no_internal_fields_and_neither_type_nor_id(fake_bus, monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=("public", "private")))
    _no_http(monkeypatch)

    await sender._deliver(LOCAL_HEAD, "https://example.com/actors/alice")

    assert fake_bus.topic("local_delivery").published[0]["payload"]["activity"] == \
           {"actor": "https://example.com/actors/bob", "object": "https://example.com/actors/alice"}


@pytest.mark.asyncio
async def test_a_local_delivery_is_published_once_however_often_it_is_tried(fake_bus, monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=("public", "private")))
    _no_http(monkeypatch)

    await sender._deliver(LOCAL_HEAD, "https://example.com/actors/alice")
    await sender._deliver(LOCAL_HEAD, "https://example.com/actors/alice")

    assert len(fake_bus.topic("local_delivery").published) == 1


@pytest.mark.asyncio
async def test_an_unknown_local_user_is_not_delivered_to(fake_bus, monkeypatch):
    storage_module._instance = Mock(get_user_key=AsyncMock(return_value=None))
    fetch, post = _no_http(monkeypatch)

    assert await sender._deliver(LOCAL_HEAD, "https://example.com/actors/nobody") is False
    assert fake_bus.topic("local_delivery").published == []
    post.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_instance_actor_takes_the_delivery_and_discards_it(fake_bus, monkeypatch):
    fetch, post = _no_http(monkeypatch)

    assert await sender._deliver(LOCAL_HEAD, "https://example.com/actor") is True
    assert fake_bus.topic("local_delivery").published == []
    post.assert_not_awaited()

