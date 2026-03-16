# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
import asyncpg


class _storage:
    def __init__(self, pool: asyncpg.Pool, schema_name: str):
        self._pool = pool
        self._schema_name = schema_name

    async def ensure_table(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                               CREATE TABLE IF NOT EXISTS {self._schema_name}.webfinger_users (
                                   username TEXT PRIMARY KEY
                               )
                               """)

    async def user_exists(self, username: str) -> str | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(f"""
                                      SELECT count(*) c
                                      FROM {self._schema_name}.webfinbger_users
                                      WHERE username = $1
                                      """,
                                      username)
            return (row["c"] > 0)


    async def add(self, username: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                               INSERT INTO {self._schema_name}.webfinger_users (username)
                               VALUES ($1)
                               ON CONFLICT (username) DO NOTHING
                               """,
                               username)


    async def delete(self, username: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                               DELETE FROM {self._schema_name}.webfinger_users
                               WHERE acct = $1
                               """,
                               username)


_instance: _storage | None = None


async def init(component_name: str, config: Dict[str, str]) -> None:
    global _instance
    pool = await asyncpg.create_pool(host=config["host"],
                                     port=int(config["port"]),
                                     database=config["database"],
                                     user=config["user"],
                                     password=config["password"],)
    _instance = _storage(pool, component_name)


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Webfinger Storage is not initialized.")
    return _instance
