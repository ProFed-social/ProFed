# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from functools import wraps
from typing import Any, Optional
import asyncpg

from profed.core.persistence.db_connections import fetch_pool


def wait_for_rebuild(f):
    @wraps(f)
    async def wrapper(self, *args, **kwargs):
        if self._is_rebuilt is not None:
            await self._is_rebuilt.wait()
            self._is_rebuilt = None

        return await f(self, *args, **kwargs)

    return wrapper


class BaseStorage:
    def __init__(self,
                 pool: asyncpg.Pool):
        self._pool = pool
        self._is_rebuilt = asyncio.Event()

    def rebuild_finished(self) -> None:
        if self._is_rebuilt is not None:
            self._is_rebuilt.set()

    async def execute(self, sql: str, *args: Any) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(sql, *args)

    @wait_for_rebuild
    async def fetch_one(self, sql: str, *args: Any) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)

        return dict(row) if row is not None else None

    @wait_for_rebuild
    async def fetch_all(self, sql: str, *args: Any) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)

        return [dict(row) for row in rows]


async def init_pool(config: dict) -> asyncpg.Pool:
    return await fetch_pool(host=config["host"],
                            port=int(config["port"]),
                            database=config["database"],
                            user=config["user"],
                            password=config["password"],
                            min_size=int(config["pool_min_size"]),
                            max_size=int(config["pool_max_size"]))

