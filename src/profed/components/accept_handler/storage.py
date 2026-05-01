# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncpg
from profed.core.db_connections import fetch_pool
 
 
class _Storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
 
    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DROP SCHEMA IF EXISTS accept_handler CASCADE")
            await conn.execute("CREATE SCHEMA IF NOT EXISTS accept_handler")
            await conn.execute("""CREATE TABLE IF NOT EXISTS
                                  accept_handler.known_actor_ids (actor_url TEXT PRIMARY KEY,
                                                                  account_id BIGINT NOT NULL)""")
 
    async def upsert(self, actor_url: str, account_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO accept_handler.known_actor_ids (actor_url, account_id)
                                  VALUES ($1, $2)
                                  ON CONFLICT (actor_url) DO UPDATE
                                      SET account_id = EXCLUDED.account_id""",
                               actor_url,
                               account_id)
 
    async def get_by_actor_url(self, actor_url: str) -> int | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT account_id FROM accept_handler.known_actor_ids
                                         WHERE actor_url = $1""",
                                      actor_url)
        return row["account_id"] if row is not None else None
 
 
_instance: _Storage | None = None
 
 
async def init(config: dict) -> None:
    global _instance
    pool = await fetch_pool(host=config["host"],
                            port=int(config["port"]),
                            database=config["database"],
                            user=config["user"],
                            password=config["password"],
                            min_size=int(config["pool_min_size"]),
                            max_size=int(config["pool_max_size"]))
    _instance = _Storage(pool)
 
 
async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("accept_handler storage not initialized")
    return _instance

