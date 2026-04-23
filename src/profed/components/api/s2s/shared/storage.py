# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Callable, Tuple, Any, Awaitable
import asyncpg
from profed.core.db_connections import fetch_pool

def build_storage(table_name: str) \
    -> Tuple[Callable[[Dict[str, str]], Awaitable[None]],
             Callable[[], Awaitable[Any]],
             Callable[[Any], None],
             Callable[[Any], None]]:
    class _storage:
        def __init__(self, pool: asyncpg.Pool):
            nonlocal table_name

            self._pool = pool
            self._table_name = table_name

        async def ensure_table(self) -> None:
            async with self._pool.acquire() as conn:
                await conn.execute(f"""
                                   CREATE TABLE IF NOT EXISTS api.{self._table_name} (
                                       username TEXT PRIMARY KEY
                                   )
                                   """)

        async def exists(self, username: str) -> str | None:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                                          SELECT count(*) c
                                          FROM api.{self._table_name}
                                          WHERE username = $1
                                          """,
                                          username)
                return (row["c"] > 0)


        async def add(self, username: str) -> None:
            async with self._pool.acquire() as conn:
                await conn.execute(f"""
                                   INSERT INTO api.{self._table_name} (username)
                                   VALUES ($1)
                                   ON CONFLICT (username) DO NOTHING
                                   """,
                                   username)


        async def delete(self, username: str) -> None:
            async with self._pool.acquire() as conn:
                await conn.execute(f"""
                                   DELETE FROM api.{self._table_name}
                                   WHERE acct = $1
                                   """,
                                   username)


    _instance: _storage | None = None


    async def init(config: Dict[str, str]) -> None:
        nonlocal _instance
        pool = await fetch_pool(host=config["host"],
                                port=int(config["port"]),
                                database=config["database"],
                                user=config["user"],
                                password=config["password"],)
        _instance = _storage(pool)


    async def storage() -> _storage:
        nonlocal table_name, _instance

        if _instance is None:
            raise RuntimeError(f"{table_name.capitalize()} storage is not initialized.")
        return _instance


    def overwrite(s):
        nonlocal _instance

        _instance = s


    def reinit(pool):
        overwrite(_storage(pool))


    return init, storage, overwrite, reinit

