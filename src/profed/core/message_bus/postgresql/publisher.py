# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from typing import Callable, Dict, Any, Coroutine
from asyncpg import Pool, Connection
from asyncpg.transaction import Transaction


def _publish(conn: Connection, topic: str, schema: str) \
        -> Callable[[str, str, Dict[str, Any] | None, int | None], Coroutine[Any, Any, int | None]]:
    async def publish(event_type: str,
                      object_id:  str,
                      payload:    Dict[str, Any] | None = None,
                      message_id=None) -> int | None:
        row = await conn.fetchrow(f"""
                           INSERT INTO {schema}.{topic}
                                       (event_type, object_id, payload, message_id)
                           VALUES ($1, $2, $3, $4)
                           ON CONFLICT (message_id) DO NOTHING
                           RETURNING id
                           """,
                           event_type,
                           object_id,
                           payload if payload is not None else {},
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

    async def __aenter__(self) \
            -> Callable[[str, str, Dict[str, Any] | None, int | None], Coroutine[Any, Any, int | None]]:
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

