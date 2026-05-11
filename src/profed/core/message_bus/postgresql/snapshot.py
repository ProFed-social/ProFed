# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Dict, Any, Awaitable
from asyncpg import Connection, Pool 
from asyncpg.transaction import Transaction

def _publish_snapshot(conn: Connection, topic: str, schema: str) \
        -> Callable[[Dict[str, Any], int], Awaitable[None]]:
    async def publish(snapshot: Dict[str, Any], last_event_id: int) -> None:
        await conn.execute(f"""
                           INSERT INTO {schema}.{topic}_snapshots (payload, last_event_id)
                           VALUES ($1, $2)
                           """,
                           snapshot,
                           last_event_id)
    return publish


class SnapshotPublisher:
    def __init__(self, pool: Pool, schema: str, topic: str):
        self._pool: Pool = pool
        self._schema: str = schema
        self._topic: str = topic
        self._context = None
        self._conn: Connection | None = None
        self._tx: Transaction | None = None

    async def __aenter__(self) -> Callable[[Dict[str, Any], int], Awaitable[None]]:
        self._context = self._pool.acquire()
        self._conn = await self._context.__aenter__()
        self._tx = self._conn.transaction()
        await self._tx.start()
        return _publish_snapshot(self._conn, self._topic, self._schema)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type:
                await self._tx.rollback()
                raise exc
            else:
                await self._tx.commit()
                await self._conn.execute(f"NOTIFY {self._schema}_{self._topic}_snapshot")
        finally:
            await self._context.__aexit__(exc_type, exc, tb)


async def last_snapshot(pool: Pool, schema: str, topic: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"""
                                  SELECT last_event_id, payload 
                                  FROM {schema}.{topic}_snapshots
                                  ORDER BY last_event_id DESC
                                  LIMIT 1
                                  """)
        return (row["last_event_id"],row["payload"]) if row else (0, [])


async def last_snapshot_id(pool: Pool, schema: str, topic: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"""
                                  SELECT MAX(last_event_id) AS last_event_id
                                  FROM {schema}.{topic}_snapshots
                                  """)
        return row["last_event_id"] or 0

