# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
import random


logger = logging.getLogger(__name__)

IDLE_LIMIT = 15
FAILURE_LIMIT = 5
BACKOFF_MIN = 1.0
BACKOFF_MAX = 60.0
JITTER = 0.1
SLEEP_MIN = 10.0
SLEEP_MAX = 30.0


async def jittered_sleep(seconds: float | None = None) -> None:
    await asyncio.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX)
                        if seconds is None else
                        seconds + random.uniform(0.0, min(max(seconds, 0.0) * JITTER, SLEEP_MAX)))


class KeyedWorkers:
    def __init__(self,
                 step,
                 *,
                 name="worker",
                 idle_limit=IDLE_LIMIT,
                 failure_limit=FAILURE_LIMIT,
                 sleep=jittered_sleep):
        self._step = step
        self._name = name
        self._idle_limit = idle_limit
        self._failure_limit = failure_limit
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
        if key in self._tasks:
            return

        queue = self._queues.get(key)
        if queue is None or queue.empty():
            self._queues.pop(key, None)
        elif self._started:
            self._spawn(key)

    async def _work(self, key) -> tuple[float | None, bool]:
        try:
            return await self._step(key, self.queue(key)), True
        except Exception:
            logger.exception("%s:%s failed", self._name, key)
            return None, False

    async def _run(self, key) -> None:
        idle = 0
        failures = 0
        backoff = 0.0

        while True:
            due_in, succeeded = await self._work(key)

            if not succeeded:
                failures += 1
                if failures > self._failure_limit:
                    logger.error("%s:%s abandoned after %d failures", self._name, key, failures - 1)
                    self._queues.pop(key, None)
                    return
                backoff = min(max(2 * backoff, BACKOFF_MIN), BACKOFF_MAX)
                await self._sleep(backoff)
                continue

            failures, backoff = 0, 0.0
            if due_in is None and not self._idle_limit:
                return

            idle = idle + 1 if due_in is None else 0

            if self._idle_limit and idle >= self._idle_limit:
                self._tasks.pop(key, None)
                await self._sleep()
                due_in, _ = await self._work(key)
                if due_in is None:
                    return
                self._tasks[key] = asyncio.current_task()
                idle = 0

            await self._sleep(due_in)

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        self._started = False
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

