# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import AsyncIterator
import asyncpg


class _ListenerDict(dict):
    def __init__(self, connection, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._c = connection

    async def __getitem__(self, topic: str):
        if topic not in self:
            q = asyncio.Queue()
            super().__setitem__(topic, q)

            await self._c.add_listener(topic,
                                       lambda *a: q.put_nowait(a[2].encode()))
        return super().__getitem__(topic)


class _Mq:
    def __init__(self, connection):
        self._conn = connection
        self._listeners = _ListenerDict(connection)

    async def publish(self, topic: str, payload: bytes):
        await self._conn.execute("INSERT INTO "
                                     "messages(topic, payload) "
                                     "VALUES($1, $2)",
                                 topic,
                                 payload)
        await self._conn.execute(f"NOTIFY {topic}, $1", payload.decode())

    async def subscribe(self, topic: str) -> AsyncIterator[bytes]:
        q = await self._listeners[topic]
        while True:
            yield await q.get()


class PostgresTable:
    """
    Simple async PostgreSQL message bus using a table + NOTIFY
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = None
        self._mq = None

    async def __aenter__(self):
        self._conn = await asyncpg.connect(dsn=self.dsn)
        return _Mq(self._conn)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            await self._conn.close()
        self._conn = None

