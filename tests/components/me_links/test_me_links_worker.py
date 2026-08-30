# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from profed.components.me_links import worker
from profed.components.me_links.fetch import Page


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)

PROFILE = "https://p.test/@alice"
LINK = "https://a.test/"


def _queue(*items):
    queue = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    return queue


def _page(state, links=(), **rest):
    return Page(state, list(links), **rest)


def _published(fake_bus):
    return [(msg["event_type"], msg["object_id"]) for msg in fake_bus.topic("me_links").published]


async def _record(component, state, checked_at, stable_since, next_due_at, etag=None, content_hash=None):
    await component.record_verification(PROFILE,
                                        LINK,
                                        state,
                                        checked_at,
                                        stable_since,
                                        next_due_at,
                                        None,
                                        etag,
                                        content_hash)


async def _check(page, fake_bus, component, now=NOW):
    async def _perform(*args, **kwargs):
        return page

    with patch.object(worker.fetch, "perform", _perform), \
         patch.object(worker.instance_key, "signer", lambda: None):
        return await worker.check(PROFILE, LINK, now)


@pytest.mark.asyncio
async def test_a_page_pointing_back_verifies_the_link(fake_bus, component):
    await _check(_page("read", [PROFILE]), fake_bus, component)

    assert _published(fake_bus) == [("verified", f"{PROFILE}|{LINK}")]


@pytest.mark.asyncio
async def test_a_page_without_the_link_stays_unverified(fake_bus, component):
    await _check(_page("read", ["https://p.test/@bob"]), fake_bus, component)

    assert _published(fake_bus) == [("unverified", f"{PROFILE}|{LINK}")]


@pytest.mark.asyncio
async def test_a_missing_page_is_gone(fake_bus, component):
    await _check(_page("gone"), fake_bus, component)

    assert _published(fake_bus) == [("gone", f"{PROFILE}|{LINK}")]


@pytest.mark.asyncio
async def test_a_failed_request_publishes_nothing(fake_bus, component):
    assert await _check(_page("failed"), fake_bus, component) is False
    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_an_unchanged_page_keeps_the_previous_state(fake_bus, component):
    await _record(component, "verified", NOW - timedelta(days=2), NOW - timedelta(days=2), NOW, '"abc"', "hash")

    await _check(_page("unchanged"), fake_bus, component)

    assert _published(fake_bus) == [("verified", f"{PROFILE}|{LINK}")]


@pytest.mark.asyncio
async def test_an_unchanged_page_keeps_its_stability(fake_bus, component):
    stable_since = NOW - timedelta(days=20)
    await _record(component, "verified", NOW - timedelta(days=2), stable_since, NOW, '"abc"', "hash")

    await _check(_page("unchanged"), fake_bus, component)

    assert fake_bus.topic("me_links").published[0]["payload"]["stable_since"] == stable_since.isoformat()


@pytest.mark.asyncio
async def test_a_page_with_the_same_etag_keeps_its_stability(fake_bus, component):
    stable_since = NOW - timedelta(days=20)
    await _record(component, "verified", NOW - timedelta(days=2), stable_since, NOW, '"abc"', "hash")

    await _check(_page("read", [PROFILE], etag='"abc"'), fake_bus, component)

    assert fake_bus.topic("me_links").published[0]["payload"]["stable_since"] == stable_since.isoformat()


@pytest.mark.asyncio
async def test_a_changed_page_starts_its_stability_anew(fake_bus, component):
    await _record(component, "verified", NOW - timedelta(days=2), NOW - timedelta(days=20), NOW, '"abc"', "hash")

    await _check(_page("read", [PROFILE], etag='"different"'), fake_bus, component)

    assert fake_bus.topic("me_links").published[0]["payload"]["stable_since"] == NOW.isoformat()


@pytest.mark.asyncio
async def test_a_page_with_the_same_body_keeps_its_stability(fake_bus, component):
    stable_since = NOW - timedelta(days=20)
    await _record(component, "verified", NOW - timedelta(days=2), stable_since, NOW, None, "hash")

    await _check(_page("read", [PROFILE], content_hash="hash"), fake_bus, component)

    assert fake_bus.topic("me_links").published[0]["payload"]["stable_since"] == stable_since.isoformat()


@pytest.mark.asyncio
async def test_a_check_publishes_what_it_found(fake_bus, component):
    await _check(_page("read", [PROFILE], etag='"abc"'), fake_bus, component)

    payload = fake_bus.topic("me_links").published[0]["payload"]

    assert payload["etag"] == '"abc"'
    assert payload["checked_at"] == NOW.isoformat()


@pytest.mark.asyncio
async def test_a_check_writes_nothing_itself(fake_bus, component):
    await _check(_page("read", [PROFILE]), fake_bus, component)

    assert await component.verification(PROFILE, LINK) is None


@pytest.mark.asyncio
async def test_a_step_without_a_previous_check_looks_at_the_page(fake_bus, component):
    async def _perform(*args, **kwargs):
        return _page("read", [PROFILE])

    with patch.object(worker.fetch, "perform", _perform), \
         patch.object(worker.instance_key, "signer", lambda: None):
        assert await worker.step((PROFILE, LINK), _queue()) == 0.0


@pytest.mark.asyncio
async def test_a_step_on_a_fresh_check_does_nothing(fake_bus, component):
    now = datetime.now(timezone.utc)
    await _record(component, "verified", now, now, now + timedelta(days=1))

    assert await worker.step((PROFILE, LINK), _queue()) is None


@pytest.mark.asyncio
async def test_a_failed_step_asks_to_come_back(fake_bus, component):
    async def _perform(*args, **kwargs):
        return _page("failed")

    with patch.object(worker.fetch, "perform", _perform), \
         patch.object(worker.instance_key, "signer", lambda: None):
        assert await worker.step((PROFILE, LINK), _queue()) == 300.0

