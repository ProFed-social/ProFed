# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from typing import Callable, Dict, Any, Awaitable
import json
from asyncpg import Pool, Connection, Transaction

def _publish(conn: Connection, topic: str, schema: str) \
        -> Callable[[Dict[str, Any]], Awaitable[None]]:
    async def publish(message: Dict[str, Any]) -> None:
        await conn.execute(
            f"""
            INSERT INTO {schema}.{topic} (payload)
            VALUES ($1)
            """,
            json.dumps(message),
        )
    return publish


class Publisher:
    def __init__(self, pool: Pool, schema: str, topic: str):
        self._pool: Pool = pool
        self._schema: str = schema
        self._topic: str = topic
        self._conn: Connection | None = None
        self._tx: Transaction | None = None

    async def __aenter__(self) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        self._conn = await self._pool.acquire()
        self._tx = self._conn.transaction()
        await self._tx.start()
        return _publish(self._conn, self._topic, self._schema)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._tx is not None:
            if exc_type:
                await self._tx.rollback()
                raise exc
            else:
                await self._tx.commit()
                await self._conn.execute(f"NOTIFY {self._schema}_{self._topic}")
        await self._pool.release(self._conn)
