# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List
import asyncpg
from profed.core.db_connections import fetch_pool

class _storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def ensure_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""CREATE TABLE IF NOT EXISTS api.s2s_outbox (
                                   username TEXT NOT NULL,
                                   created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                   activity JSONB NOT NULL)
                               """)
            await conn.execute(f"""CREATE INDEX IF NOT EXISTS outbox_username_created_at_idx
                                   ON api.s2s_outbox (username, created_at)
                               """)

    async def add(self, username: str, activity: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""INSERT INTO api.s2s_outbox (username, activity)
                                   VALUES ($1, $2)
                               """,
                               username,
                               activity)

    async def fetch(self, username: str) -> List[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""SELECT activity
                                        FROM api.s2s_outbox
                                        WHERE username = $1
                                        ORDER BY created_at
                                    """,
                                    username)
            return [row["activity"] for row in rows]


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    pool = await fetch_pool(host=config["host"],
                            port=int(config["port"]),
                            database=config["database"],
                            user=config["user"],
                            password=config["password"],
                            min_size=int(config["pool_min_size"]),
                            max_size=int(config["pool_max_size"]))
    _instance = _storage(pool)


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Outbox storage is not initialized.")
    return _instance

