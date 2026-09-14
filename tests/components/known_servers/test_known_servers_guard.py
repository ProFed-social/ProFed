# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from profed.components.known_servers import guard, worker


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_a_host_without_a_check_is_submitted(component):
    await component.remember_host("a.test")

    assert await guard.submit_unchecked() == 1
    assert worker.workers().submitted == ["a.test"]


@pytest.mark.asyncio
async def test_a_host_that_was_checked_is_not_submitted_again(component):
    await component.remember_host("a.test")
    await component.record_check("a.test", NOW, NOW, NOW + timedelta(days=1), 0, None, None, None)

    assert await guard.submit_unchecked() == 0


@pytest.mark.asyncio
async def test_a_due_host_is_submitted(component):
    await component.remember_host("a.test")
    await component.record_check("a.test", NOW, NOW, NOW, 0, None, None, None)

    assert await guard.visit_due(NOW) == 1
    assert worker.workers().submitted == ["a.test"]


@pytest.mark.asyncio
async def test_a_host_that_is_not_due_stays_alone(component):
    await component.remember_host("a.test")
    await component.record_check("a.test", NOW, NOW, NOW + timedelta(days=1), 0, None, None, None)

    assert await guard.visit_due(NOW) == 0


@pytest.mark.asyncio
async def test_a_lost_host_is_never_submitted_again(component):
    await component.remember_host("a.test")
    await component.record_check("a.test", NOW, NOW, NOW - timedelta(days=1), 3, None, None, None)
    await component.forget_host("a.test")

    assert await guard.sweep({}) == 0

