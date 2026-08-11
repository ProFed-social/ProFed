# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.api.c2s.shared.statuses import compressor
 
 
TUNING = {"sleep_min": 1.0, "sleep_max": 61.0, "agility": 50.0, "sample_size": 7}
 
 
async def _slept_for(changed):
    with patch("asyncio.sleep", AsyncMock()) as slept:
        await compressor.Compressor(TUNING).sleep_after_changed(changed)
    return slept.await_args.args[0]
 
 
def test_construction_falls_back_to_the_module_defaults():
    instance = compressor.Compressor({})
 
    assert instance.sample_size == compressor.SAMPLE_SIZE
    assert instance.sleep_min == compressor.SLEEP_MIN
    assert instance.sleep_max == compressor.SLEEP_MAX
    assert instance.agility == compressor.AGILITY
 
 
@pytest.mark.asyncio
async def test_idle_waits_the_maximum():
    assert await _slept_for(0) == 61.0
 
 
@pytest.mark.asyncio
async def test_at_agility_the_wait_is_the_midpoint():
    assert await _slept_for(50) == 31.0
 
 
@pytest.mark.asyncio
async def test_a_busy_pass_approaches_the_minimum():
    assert await _slept_for(50_000) < 2.0
 
 
@pytest.mark.asyncio
async def test_the_loop_compresses_with_the_sample_size_then_sleeps_with_the_change_count():
    store = Mock(compress_all=AsyncMock(return_value=3))
    slept = []
 
    async def stop(changed):
        slept.append(changed)
        raise asyncio.CancelledError
 
    instance = compressor.Compressor(TUNING)
    with patch.object(compressor, "storage", AsyncMock(return_value=store)), \
         patch.object(instance, "sleep_after_changed", stop):
        with pytest.raises(asyncio.CancelledError):
            await instance()
 
    store.compress_all.assert_awaited_once_with(7)
    assert slept == [3]

