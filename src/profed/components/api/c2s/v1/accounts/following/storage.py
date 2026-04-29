# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncpg
from profed.core.db_connections import fetch_pool
 
 
class _Storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
 
    async def ensure_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS api.following (
                                  account_id     BIGINT  NOT NULL
                                      REFERENCES api.known_accounts (account_id),
                                  following_user TEXT    NOT NULL,
                                  accepted       BOOLEAN NOT NULL DEFAULT FALSE,
                                  PRIMARY KEY (account_id, following_user))""")
 
    async def upsert(self,
                     account_id: int,
                     following_user: str,
                     accepted: bool) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO api.following (account_id,
                                                             following_user,
                                                             accepted)
                                  VALUES ($1, $2, $3)
                                  ON CONFLICT (account_id, following_user) DO UPDATE
                                      SET accepted = EXCLUDED.accepted""",
                               account_id,
                               following_user,
                               accepted)
 
    async def delete(self,
                     account_id: int,
                     following_user: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""DELETE FROM api.following
                                  WHERE account_id = $1 AND following_user = $2""",
                               account_id,
                               following_user)
 
    async def get(self,
                  account_id: int,
                  following_user: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT account_id, following_user, accepted
                                         FROM api.following
                                         WHERE account_id = $1 AND following_user = $2""",
                                      account_id,
                                      following_user)
        return dict(row) if row is not None else None
 
 
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
        raise RuntimeError("following storage not initialized")
    return _instance

