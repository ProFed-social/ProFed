# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List
import asyncpg


class _storage:
    def __init__(self, pool: asyncpg.Pool, schema_name: str):
        self._pool = pool
        self._schema_name = schema_name

    async def ensure_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""CREATE TABLE IF NOT EXISTS {self._schema_name}.outbox (
                                   username TEXT NOT NULL,
                                   created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                   activity JSONB NOT NULL)
                               """)
            await conn.execute(f"""CREATE INDEX IF NOT EXISTS outbox_username_created_at_idx
                                   ON {self._schema_name}.outbox (username, created_at)
                               """)

    async def add(self, username: str, activity: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""INSERT INTO {self._schema_name}.outbox (username, activity)
                                   VALUES ($1, $2)
                               """,
                               username,
                               activity)

    async def fetch(self, username: str) -> List[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""SELECT activity
                                        FROM {self._schema_name}.outbox
                                        WHERE username = $1
                                        ORDER BY created_at
                                    """,
                                    username)
            return [row["activity"] for row in rows]


_instance: _storage | None = None


async def init(component_name: str, config: Dict[str, str]) -> None:
    global _instance
    pool = await asyncpg.create_pool(host=config["host"],
                                     port=int(config["port"]),
                                     database=config["database"],
                                     user=config["user"],
                                     password=config["password"])
    _instance = _storage(pool, component_name)


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Outbox storage is not initialized.")
    return _instance

