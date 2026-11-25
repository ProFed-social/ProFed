# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from asyncpg import Pool, PostgresConnectionError
from collections.abc import AsyncGenerator
import logging

from profed.core import memory
from .queries import Row, max_id
from .reader import MIN_WAIT, reader
from .stream import Stream
logger = logging.getLogger(__name__)


async def head(pool: Pool, config: dict[str, str], topic: str) -> int:
    async with pool.acquire() as conn:
        return await max_id(conn, config["schema"], topic)


async def subscribe(pool: Pool,
                    config: dict[str, str],
                    topic: str,
                    last_seen: int = 0,
                    caught_up: asyncio.Event | None = None) -> AsyncGenerator[Row, None]:
    stream = Stream(pool, config, topic, int(last_seen))
    source = reader(pool, config, topic)
    subscription = await source.register(stream)
    retry = float(config.get("minimum_message_wait", MIN_WAIT))
    caught_up_once = False

    def complain(error: Exception) -> None:
        logger.warning("subscriber could not read %s, retrying: %r", topic, error)

    try:
        while True:
            if subscription.failure is not None:
                raise subscription.failure

            if subscription.behind:
                subscription.behind = False
                target = source.position

                while True:
                    try:
                        page = await stream.page(target)
                    except (PostgresConnectionError, OSError) as error:
                        complain(error)
                        await asyncio.sleep(retry)
                        continue

                    for row in page:
                        yield row
                    if page:
                        continue
                    if not stream.held:
                        break

                    await asyncio.sleep(stream.gap_timeout)

                if not caught_up_once:
                    caught_up_once = True
                    if caught_up is not None:
                        caught_up.set()
                    memory.release()
                continue

            try:
                row = await asyncio.wait_for(subscription.queue.get(),
                                             stream.gap_timeout if stream.watching() else None)
            except TimeoutError:
                row = None

            if row is not None and row[0] > stream.position:
                yield stream.accept(row)

            if stream.watching():
                try:
                    await stream.audit()
                except (PostgresConnectionError, OSError) as error:
                    complain(error)
    finally:
        source.release(subscription)

