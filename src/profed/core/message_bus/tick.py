# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .source_key import source_key

logger = logging.getLogger(__name__)
TICK = "Tick"
_TICK_SOURCE = source_key("tick")


class Ticker:
    def __init__(self, topic, interval: float):
        self._topic = topic
        self._interval = interval
        self._last_tick = 0
        self._head = 0
        self._tasks = []

    def _observe_tick(self, sequence_id):
        self._last_tick = sequence_id

    def _observe_event(self, sequence_id):
        self._head = sequence_id

    def observe(self, sequence_id: int, event_type: str) -> None:
        (self._observe_tick
         if event_type == TICK else
         self._observe_event)(sequence_id)

    async def emit_tick_if_pending(self) -> None:
        if self._head > self._last_tick:
            async with self._topic.publish() as publish:
                await publish(TICK, "", {}, message_id=_TICK_SOURCE.message_id(self._last_tick))

    async def _track(self) -> None:
        async for sequence_id, event_type, _, _, _ in self._topic.subscribe("__ticker__"):
            self.observe(sequence_id, event_type)

    async def _emit_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self.emit_tick_if_pending()

    def start(self) -> None:
        self._tasks = [asyncio.create_task(self._track(), name="tick-track"),
                       asyncio.create_task(self._emit_loop(), name="tick-emit")]

    async def aclose(self) -> None:
        if self._tasks:
            for task in self._tasks:
                task.cancel()
                await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []


def _interval_for(cfg, name: str) -> float:
    interval = float(cfg.get(f"tick_interval_{name}", cfg.get("tick_interval", 10)))
    return interval if interval > 0 else 10


def start_tickers(bus, cfg, topic_names):
    tickers = [Ticker(bus.topic(name), _interval_for(cfg, name)) for name in topic_names]
    for ticker in tickers:
        ticker.start()
    async def aclose():
        await asyncio.gather(*(ticker.aclose() for ticker in tickers))
    return aclose()

