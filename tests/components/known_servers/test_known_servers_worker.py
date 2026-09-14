# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from profed.components.known_servers import worker
from profed.components.known_servers.fetch import NodeInfo


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)

HOST = "pleroma.test"


def _queue(*items):
    queue = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    return queue


def _fetching(info):
    return patch("profed.components.known_servers.worker.fetch.perform", AsyncMock(return_value=info))


def _published(fake_bus):
    return [(message["event_type"], message["payload"]) for message in fake_bus.topic("known_servers").published]


async def _record(component, failures=0, next_due_at=NOW, etag=None, content_hash=None):
    await component.record_check(HOST, NOW - timedelta(days=1), NOW - timedelta(days=1),
                                 next_due_at, failures, None, etag, content_hash)


@pytest.mark.asyncio
async def test_a_read_document_is_published_with_its_features(component, fake_bus):
    with _fetching(NodeInfo("read", software="pleroma", features=["pleroma_emoji_reactions"], etag='"a"')):
        await worker.check(HOST, NOW)

    verb, payload = _published(fake_bus)[0]
    assert verb == "updated"
    assert payload["software"] == "pleroma"
    assert payload["features"] == ["pleroma_emoji_reactions"]
    assert payload["failures"] == 0


@pytest.mark.asyncio
async def test_an_unchanged_document_keeps_the_stability(component, fake_bus):
    await _record(component, etag='"a"')

    with _fetching(NodeInfo("unchanged")):
        await worker.check(HOST, NOW)

    verb, payload = _published(fake_bus)[0]
    assert verb == "updated"
    assert payload["stable_since"] == (NOW - timedelta(days=1)).isoformat()
    assert payload["checked_at"] == NOW.isoformat()


@pytest.mark.asyncio
async def test_a_document_with_the_same_body_keeps_the_stability(component, fake_bus):
    await _record(component, content_hash="abc")

    with _fetching(NodeInfo("read", content_hash="abc")):
        await worker.check(HOST, NOW)

    assert _published(fake_bus)[0][1]["stable_since"] == (NOW - timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_a_changed_document_restarts_the_stability(component, fake_bus):
    await _record(component, content_hash="abc")

    with _fetching(NodeInfo("read", content_hash="def")):
        await worker.check(HOST, NOW)

    assert _published(fake_bus)[0][1]["stable_since"] == NOW.isoformat()


@pytest.mark.asyncio
async def test_a_failure_counts_up_and_keeps_the_stability(component, fake_bus):
    await _record(component, failures=1)

    with _fetching(NodeInfo("failed")):
        await worker.check(HOST, NOW)

    verb, payload = _published(fake_bus)[0]
    assert verb == "unreachable"
    assert payload["failures"] == 2
    assert payload["stable_since"] == (NOW - timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_a_failure_does_not_erase_the_known_features(component, fake_bus):
    await _record(component)

    with _fetching(NodeInfo("failed")):
        await worker.check(HOST, NOW)

    assert "features" not in _published(fake_bus)[0][1]


@pytest.mark.asyncio
async def test_enough_failures_give_the_host_up(component, fake_bus):
    await _record(component, failures=2)

    with _fetching(NodeInfo("failed")):
        await worker.check(HOST, NOW)

    assert [verb for verb, _ in _published(fake_bus)] == ["unreachable", "lost"]


@pytest.mark.asyncio
async def test_a_host_is_not_given_up_too_early(component, fake_bus):
    await _record(component, failures=0)

    with _fetching(NodeInfo("failed")):
        await worker.check(HOST, NOW)

    assert [verb for verb, _ in _published(fake_bus)] == ["unreachable"]


@pytest.mark.asyncio
async def test_a_host_that_is_not_due_is_left_alone(component, fake_bus):
    await _record(component, next_due_at=datetime.now(timezone.utc) + timedelta(days=1))

    with _fetching(NodeInfo("read")):
        assert await worker.step(HOST, _queue(HOST)) is None

    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_a_due_host_is_checked(component, fake_bus):
    await _record(component, next_due_at=datetime.now(timezone.utc) - timedelta(days=1))

    with _fetching(NodeInfo("read")):
        await worker.step(HOST, _queue(HOST))

    assert [verb for verb, _ in _published(fake_bus)] == ["updated"]


@pytest.mark.asyncio
async def test_an_unknown_host_is_checked(component, fake_bus):
    with _fetching(NodeInfo("read")):
        await worker.step(HOST, _queue(HOST))

    assert [verb for verb, _ in _published(fake_bus)] == ["updated"]

