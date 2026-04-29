# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import json
from datetime import datetime, timezone
from typing import Optional
import asyncpg
from profed.core.db_connections import fetch_pool
 
 
class _Storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
 
    async def ensure_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS api")
            await conn.execute("""CREATE TABLE IF NOT EXISTS api.known_accounts (
                                  account_id        BIGINT      PRIMARY KEY,
                                  acct              TEXT        UNIQUE NOT NULL,
                                  actor_url         TEXT        UNIQUE NOT NULL,
                                  actor_data        JSONB,
                                  last_webfinger_at TIMESTAMPTZ NOT NULL)""")
 
    async def upsert(self,
                     account_id: int,
                     acct: str,
                     actor_url: str,
                     actor_data: dict | None,
                     last_webfinger_at: datetime) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO api.known_accounts
                                    (account_id,
                                     acct,
                                     actor_url,
                                     actor_data,
                                     last_webfinger_at)
                                  VALUES ($1, $2, $3, $4, $5)
                                  ON CONFLICT (account_id) DO UPDATE
                                      SET acct              = EXCLUDED.acct,
                                          actor_url         = EXCLUDED.actor_url,
                                          actor_data        = EXCLUDED.actor_data,
                                          last_webfinger_at = EXCLUDED.last_webfinger_at""",
                               account_id,
                               acct,
                               actor_url,
                               actor_data,
                               last_webfinger_at)
 
    async def get_by_id(self, account_id: int) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT account_id, acct, actor_url,
                                             actor_data, last_webfinger_at
                                         FROM api.known_accounts
                                         WHERE account_id = $1""",
                                      account_id)
        return dict(row) if row is not None else None
 
    async def get_by_acct(self, acct: str) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT account_id, acct, actor_url,
                                            actor_data, last_webfinger_at
                                         FROM api.known_accounts
                                         WHERE acct = $1""",
                                      acct)
        return dict(row) if row is not None else None
 
    async def get_by_actor_url(self, actor_url: str) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT account_id, acct, actor_url,
                                            actor_data, last_webfinger_at
                                         FROM api.known_accounts
                                         WHERE actor_url = $1""",
                                      actor_url)
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
        raise RuntimeError("known_accounts storage not initialized")
    return _instance

