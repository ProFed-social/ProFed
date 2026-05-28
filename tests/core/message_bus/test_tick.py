# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from _fakes.message_bus import FakeTopic
from profed.core.message_bus.tick import Ticker, TICK


def _ticks(topic):
    return [m for m in topic.published if m["event_type"] == TICK]


@pytest.mark.asyncio
async def test_no_tick_without_events():
    topic = FakeTopic()
    ticker = Ticker(topic, interval=10)

    await ticker.emit_tick_if_pending()

    assert _ticks(topic) == []


@pytest.mark.asyncio
async def test_tick_emitted_when_head_advanced():
    topic = FakeTopic()
    ticker = Ticker(topic, interval=10)

    ticker.observe(5, "created")
    await ticker.emit_tick_if_pending()

    assert len(_ticks(topic)) == 1


@pytest.mark.asyncio
async def test_no_tick_when_already_ticked():
    topic = FakeTopic()
    ticker = Ticker(topic, interval=10)

    ticker.observe(5, "created")
    ticker.observe(6, TICK)
    await ticker.emit_tick_if_pending()

    assert _ticks(topic) == []


@pytest.mark.asyncio
async def test_repeated_emit_dedups_to_one_tick():
    topic = FakeTopic()
    ticker = Ticker(topic, interval=10)

    ticker.observe(5, "created")
    await ticker.emit_tick_if_pending()
    await ticker.emit_tick_if_pending()

    assert len(_ticks(topic)) == 1


@pytest.mark.asyncio
async def test_new_tick_after_new_event():
    topic = FakeTopic()
    ticker = Ticker(topic, interval=10)

    ticker.observe(5, "created")
    await ticker.emit_tick_if_pending()

    ticker.observe(6, TICK)
    ticker.observe(7, "created")
    await ticker.emit_tick_if_pending()

    assert len(_ticks(topic)) == 2

