# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging


logger = logging.getLogger(__name__)


def _make_notifier():
    channels: dict[str, set] = {}
    lock = asyncio.Lock()
    connection = None

    def _notify(_conn, _pid, channel, _payload) -> None:
        for event in channels.get(channel, ()):
            event.set()

    def _alive() -> bool:
        return connection is not None and not connection.is_closed()

    async def _connect(pool) -> None:
        nonlocal connection
        connection = await pool.acquire()
        for channel in channels:
            await connection.add_listener(channel, _notify)

    async def listen(pool, channel: str, event: asyncio.Event) -> None:
        nonlocal connection
        async with lock:
            known = channels.setdefault(channel, set())
            known.add(event)

            if not _alive():
                connection = None
                await _connect(pool)
            elif len(known) == 1:
                await connection.add_listener(channel, _notify)

    async def forget(channel: str, event: asyncio.Event) -> None:
        async with lock:
            listeners = channels.get(channel, set())
            listeners.discard(event)
            if listeners or channel not in channels:
                return

            del channels[channel]
            if _alive():
                try:
                    await connection.remove_listener(channel, _notify)
                except Exception as exc:
                    logger.warning("could not stop listening on %s: %r", channel, exc)

    def listener_count() -> int:
        return sum(len(events) for events in channels.values())

    return listen, forget, listener_count


listen, forget, listener_count = _make_notifier()

