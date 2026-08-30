# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from profed.components.me_links import guard, worker


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)

CONFIG = {"min_wait": timedelta(days=1), "max_wait": timedelta(days=30), "ramp": timedelta(days=90)}

PROFILE = "https://p.test/@alice"
LINK = "https://a.test/"


def _submitted():
    return worker.workers().submitted


def _published(fake_bus):
    return [(msg["event_type"], msg["object_id"]) for msg in fake_bus.topic("me_links").published]


async def _verified(component, next_due_at, still_listed=True):
    if still_listed:
        await component.replace_links(PROFILE, [LINK])
    await component.record_verification(PROFILE,
                                        LINK,
                                        "verified",
                                        NOW - timedelta(days=10),
                                        NOW - timedelta(days=10),
                                        next_due_at,
                                        None,
                                        None,
                                        None)


@pytest.mark.asyncio
async def test_a_new_link_is_submitted(fake_bus, component):
    await component.replace_links(PROFILE, [LINK])

    assert await guard.submit_unchecked() == 1
    assert _submitted() == [(PROFILE, LINK)]


@pytest.mark.asyncio
async def test_an_already_checked_link_is_not_submitted_again(fake_bus, component):
    await _verified(component, NOW + timedelta(days=1))

    assert await guard.submit_unchecked() == 0


@pytest.mark.asyncio
async def test_a_due_link_is_submitted_for_a_new_check(fake_bus, component):
    await _verified(component, NOW - timedelta(hours=1))

    assert await guard.visit_due(NOW) == 1
    assert _submitted() == [(PROFILE, LINK)]


@pytest.mark.asyncio
async def test_a_link_that_is_not_due_stays_untouched(fake_bus, component):
    await _verified(component, NOW + timedelta(days=1))

    assert await guard.visit_due(NOW) == 0
    assert _submitted() == []


@pytest.mark.asyncio
async def test_a_due_link_the_actor_dropped_is_deleted(fake_bus, component):
    await _verified(component, NOW - timedelta(hours=1), still_listed=False)

    await guard.visit_due(NOW)

    assert _published(fake_bus) == [("deleted", f"{PROFILE}|{LINK}")]


@pytest.mark.asyncio
async def test_a_deleted_link_is_forgotten(fake_bus, component):
    await _verified(component, NOW - timedelta(hours=1), still_listed=False)

    await guard.visit_due(NOW)

    assert await component.verification(PROFILE, LINK) is None


@pytest.mark.asyncio
async def test_a_dropped_link_that_is_not_due_is_kept_for_now(fake_bus, component):
    await _verified(component, NOW + timedelta(days=1), still_listed=False)

    await guard.visit_due(NOW)

    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_a_sweep_covers_new_and_due_links(fake_bus, component):
    await component.replace_links(PROFILE, [LINK, "https://b.test/"])
    await component.record_verification(PROFILE,
                                        LINK,
                                        "verified",
                                        NOW - timedelta(days=10),
                                        NOW - timedelta(days=10),
                                        NOW - timedelta(hours=1),
                                        None,
                                        None,
                                        None)

    assert await guard.sweep(CONFIG) == 2

