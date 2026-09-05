# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.api.c2s.shared.statuses import sweeper
from _fakes import background_task_driver as driver


TUNING = {"sleep_min": 1.0, "sleep_max": 5.0, "agility": 2.0}


@pytest.mark.asyncio
async def test_a_pass_sweeps_the_orphaned_counters():
    store = Mock(sweep_orphans=AsyncMock(return_value=3))
    run, _unused = driver(sweeper, TUNING, store)

    await run()

    store.sweep_orphans.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_an_idle_pass_waits_the_configured_maximum():
    store = Mock(sweep_orphans=AsyncMock(return_value=0))
    run, slept = driver(sweeper, TUNING, store)

    await run()

    assert slept == [5.0]


@pytest.mark.asyncio
async def test_a_busy_pass_waits_shorter_than_an_idle_one():
    busy_run, busy = driver(sweeper, TUNING, Mock(sweep_orphans=AsyncMock(return_value=100)))
    idle_run, idle = driver(sweeper, TUNING, Mock(sweep_orphans=AsyncMock(return_value=0)))

    await busy_run()
    await idle_run()

    assert busy[0] < idle[0]


@pytest.mark.asyncio
async def test_a_failing_pass_is_logged_and_counted_as_idle():
    store = Mock(sweep_orphans=AsyncMock(side_effect=RuntimeError("boom")))
    run, slept = driver(sweeper, TUNING, store)

    with patch.object(sweeper.logger, "exception") as reported:
        await run()

    reported.assert_called_once()
    assert slept == [5.0]


@pytest.mark.asyncio
async def test_the_loop_keeps_running_after_a_failing_pass():
    store = Mock(sweep_orphans=AsyncMock(side_effect=[RuntimeError("boom"), 100]))
    run, slept = driver(sweeper, TUNING, store, stop_after=2)

    with patch.object(sweeper.logger, "exception"):
        await run()

    assert len(slept) == 2
    assert slept[1] < slept[0]

