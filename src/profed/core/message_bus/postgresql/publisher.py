# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from typing import Callable, Dict, Any, Awaitable
from asyncpg import Pool, Connection 
from asyncpg.transaction import Transaction
import json

def _publish(conn: Connection, topic: str, schema: str) \
        -> Callable[[Dict[str, Any]], Awaitable[None]]:
    async def publish(message: Dict[str, Any], message_id=None) -> None:
        row = await conn.fetchrow(f"""
                           INSERT INTO {schema}.{topic} (payload, message_id)
                           VALUES ($1, $2)
                           ON CONFLICT (message_id) DO NOTHING
                           RETURNING id
                           """,
                           json.dumps(message),
                           message_id)
        return None if row is None else row["id"]
    return publish


class Publisher:
    def __init__(self, pool: Pool, schema: str, topic: str):
        self._pool: Pool = pool
        self._schema: str = schema
        self._topic: str = topic
        self._context = None
        self._conn: Connection | None = None
        self._tx: Transaction | None = None

    async def __aenter__(self) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        self._context = self._pool.acquire()
        self._conn = await self._context.__aenter__()
        self._tx = self._conn.transaction()
        await self._tx.start()
        return _publish(self._conn, self._topic, self._schema)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if self._tx is not None:
                if exc_type:
                    await self._tx.rollback()
                    raise exc
                else:
                    await self._tx.commit()
                    await self._conn.execute(f"NOTIFY {self._schema}_{self._topic}")
        finally:
            await self._context.__aexit__(exc_type, exc, tb)
