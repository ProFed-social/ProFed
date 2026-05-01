# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Dict, List, Optional
import asyncpg
from profed.core.db_connections import fetch_pool 
 
class _storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
 
    async def ensure_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS api.c2s_home_timeline (
                                   id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                                   username   TEXT        NOT NULL,
                                   created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                   activity   JSONB       NOT NULL)""")
            await conn.execute("""CREATE INDEX IF NOT EXISTS c2s_home_timeline_username_idx
                                   ON api.c2s_home_timeline (username, created_at DESC)""")
 
    async def add(self, username: str, activity: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO api.c2s_home_timeline (username, activity)
                                   VALUES ($1, $2)""",
                               username,
                               activity)
 
    async def fetch(self,
                    username: str,
                    limit: int = 20,
                    max_id: Optional[str] = None,
                    since_id: Optional[str] = None) -> List[tuple[str, dict]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""SELECT id::text, activity
                                        FROM api.c2s_home_timeline
                                        WHERE username = $1
                                        ORDER BY created_at DESC
                                        LIMIT $2""",
                                    username,
                                    limit)
            return [(row["id"], row["activity"]) for row in rows]
 
 
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
        raise RuntimeError("Home timeline storage is not initialized.")
    return _instance

