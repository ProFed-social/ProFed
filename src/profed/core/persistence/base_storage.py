# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Optional
import asyncpg
from profed.core.persistence.db_connections import fetch_pool


class BaseStorage:
    def __init__(self,
                 pool: asyncpg.Pool,
                 schema: str | None,
                 subscriber_schemas: list[str] | None = None):
        self._pool = pool
        self._schema = schema
        self._subscriber_schemas = subscriber_schemas or []

    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            for sub in self._subscriber_schemas:
                await conn.execute(f"DROP SCHEMA IF EXISTS {sub} CASCADE")

            if self._schema is not None:
                await conn.execute(f"DROP SCHEMA IF EXISTS {self._schema} CASCADE")
                await conn.execute(f"CREATE SCHEMA {self._schema}")

    async def execute(self, sql: str, *args: Any) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(sql, *args)

    async def fetch_one(self, sql: str, *args: Any) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)

        return dict(row) if row is not None else None

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

