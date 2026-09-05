# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.api.c2s.shared.statuses import compressor
from _fakes import background_task_driver as driver


TUNING = {"sample_size": 7, "sleep_min": 1.0, "sleep_max": 5.0, "agility": 2.0}


@pytest.mark.asyncio
async def test_a_pass_compresses_with_the_configured_sample_size():
    store = Mock(compress_all=AsyncMock(return_value=3))
    run, _unused = driver(compressor, TUNING, store)

    await run()

    store.compress_all.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_an_idle_pass_waits_the_configured_maximum():
    store = Mock(compress_all=AsyncMock(return_value=0))
    run, slept = driver(compressor, TUNING, store)

    await run()

    assert slept == [5.0]


@pytest.mark.asyncio
async def test_at_the_agility_the_wait_is_the_midpoint():
    store = Mock(compress_all=AsyncMock(return_value=2))
    run, slept = driver(compressor, TUNING, store)

    await run()

    assert slept == [3.0]


@pytest.mark.asyncio
async def test_a_busy_pass_approaches_the_configured_minimum():
    store = Mock(compress_all=AsyncMock(return_value=100000))
    run, slept = driver(compressor, TUNING, store)

    await run()

    assert slept[0] == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
async def test_a_failing_pass_is_logged_and_counted_as_idle():
    store = Mock(compress_all=AsyncMock(side_effect=RuntimeError("boom")))
    run, slept = driver(compressor, TUNING, store)

    with patch.object(compressor.logger, "exception") as reported:
        await run()

    reported.assert_called_once()
    assert slept == [5.0]


@pytest.mark.asyncio
async def test_the_loop_keeps_running_after_a_failing_pass():
    store = Mock(compress_all=AsyncMock(side_effect=[RuntimeError("boom"), 100000]))
    run, slept = driver(compressor, TUNING, store, stop_after=2)

    with patch.object(compressor.logger, "exception"):
        await run()

    assert len(slept) == 2
    assert slept[1] < slept[0]

