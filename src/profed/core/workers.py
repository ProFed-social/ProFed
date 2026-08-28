# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
import random


logger = logging.getLogger(__name__)

IDLE_LIMIT = 15
SLEEP_MIN = 10.0
SLEEP_MAX = 30.0


async def jittered_sleep(minimum: float = SLEEP_MIN, maximum: float = SLEEP_MAX) -> None:
    await asyncio.sleep(random.uniform(minimum, maximum))


class KeyedWorkers:
    def __init__(self, step, *, name="worker", idle_limit=IDLE_LIMIT, sleep=jittered_sleep):
        self._step = step
        self._name = name
        self._idle_limit = idle_limit
        self._sleep = sleep
        self._queues: dict = {}
        self._tasks: dict = {}
        self._started = False

    def queue(self, key) -> asyncio.Queue:
        return self._queues.setdefault(key, asyncio.Queue())

    def start(self, keys=()) -> None:
        self._started = True
        for key in keys:
            self.ensure_task(key)

    def submit(self, key, item=None) -> None:
        if item is not None:
            self.queue(key).put_nowait(item)
        self.ensure_task(key)

    def ensure_task(self, key) -> None:
        if self._started and key not in self._tasks:
            self._spawn(key)

    def _spawn(self, key) -> None:
        task = asyncio.create_task(self._run(key), name=f"{self._name}:{key}")
        self._tasks[key] = task
        task.add_done_callback(lambda t: self._retire(key, t))

    def _retire(self, key, task) -> None:
        if self._tasks.get(key) is task:
            self._tasks.pop(key, None)

    async def _work(self, key) -> bool:
        try:
            return bool(await self._step(key, self.queue(key)))
        except Exception:
            logger.exception("%s:%s failed", self._name, key)
            return True

    async def _run(self, key) -> None:
        idle = 0

        while True:
            idle = 0 if await self._work(key) else idle + 1

            if idle >= self._idle_limit:
                self._tasks.pop(key, None)
                await self._sleep()
                if not await self._work(key):
                    return
                self._tasks[key] = asyncio.current_task()
                idle = 0

            await self._sleep()

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        self._started = False
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

