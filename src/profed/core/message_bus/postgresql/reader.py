# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from asyncpg import Pool, PostgresConnectionError
import logging

from . import notifications
from .queries import Row, max_id
from .stream import Stream


logger = logging.getLogger(__name__)


MIN_WAIT = 0.05
MAX_WAIT = 2.0
SUBSCRIBER_QUEUE = 200


class Subscription:
    def __init__(self, stream, size: int):
        self.stream = stream
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=size)
        self.behind = True
        self.failure: BaseException | None = None

    @property
    def position(self) -> int:
        return self.stream.position


def Reader(pool: Pool, config: dict[str, str], topic: str):
    schema = config["schema"]
    channel = f"{schema}_{topic}"
    size = max(int(config.get("subscriber_queue", SUBSCRIBER_QUEUE)), 1)
    min_wait = float(config.get("minimum_message_wait", MIN_WAIT))
    max_wait = float(config.get("maximum_message_wait", MAX_WAIT))
    subscriptions: list[Subscription] = []
    stream = None
    task = None

    def deliver(rows: list[Row]) -> None:
        for subscription in (one for one in subscriptions if not one.behind):
            for row in (one for one in rows if one[0] > subscription.position):
                try:
                    subscription.queue.put_nowait(row)
                except asyncio.QueueFull:
                    subscription.behind = True
                    break

    def stopped(finished: asyncio.Task) -> None:
        error = None if finished.cancelled() else finished.exception()
        if error is None:
            return

        logger.critical("reader for %s stopped: %r", topic, error)
        for subscription in subscriptions:
            subscription.failure = error
            if not subscription.queue.full():
                subscription.queue.put_nowait(None)

    async def run() -> None:
        message_event = asyncio.Event()
        wait = min_wait

        try:
            while True:
                message_event.clear()

                try:
                    rows = await stream.page()
                except (PostgresConnectionError, OSError) as error:
                    logger.warning("reader could not read %s, retrying: %r", topic, error)
                    await asyncio.sleep(wait)
                    continue

                if rows:
                    deliver(rows)
                    wait = min_wait
                    continue

                await notifications.listen(pool, channel, message_event)
                try:
                    await asyncio.wait_for(message_event.wait(), timeout=wait)
                    wait = min_wait
                except TimeoutError:
                    wait = min(wait * 2, max_wait)
        finally:
            await notifications.forget(channel, message_event)

    class _Reader:
        @property
        def pool(self) -> Pool:
            return pool

        @property
        def position(self) -> int:
            return stream.position if stream is not None else 0

        async def register(self, own) -> Subscription:
            nonlocal stream, task
            if stream is None:
                async with pool.acquire() as conn:
                    stream = Stream(pool, config, topic, await max_id(conn, schema, topic))

            subscription = Subscription(own, size)
            subscriptions.append(subscription)
            if task is None:
                task = asyncio.create_task(run())
                task.add_done_callback(stopped)

            return subscription

        def release(self, subscription: Subscription) -> None:
            nonlocal task
            if subscription in subscriptions:
                subscriptions.remove(subscription)
            if not subscriptions and task is not None:
                task.remove_done_callback(stopped)
                task.cancel()
                task = None

    return _Reader()


_readers: dict[tuple[str, str], object] = {}


def reader(pool: Pool, config: dict[str, str], topic: str):
    key = (config["schema"], topic)
    if key not in _readers or _readers[key].pool is not pool:
        _readers[key] = Reader(pool, config, topic)

    return _readers[key]


def forget_readers() -> None:
    _readers.clear()

