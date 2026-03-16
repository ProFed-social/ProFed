# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
from asyncpg import Pool, create_pool


class _storage:
    def __init__(self, pool: Pool, schema_name: str):
        self._pool = pool
        self._schema_name = schema_name

    async def ensure_schema(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS {self._schema_name}.actor (
                                      username TEXT PRIMARY KEY,
                                      payload JSONB NOT NULL)""")

    async def add(self, username: str, payload: dict):
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO {self._schema_name}.actor (username, payload)
                                  VALUES ($1, $2)""",
                               username,
                               payload)

    async def update(self, username: str, payload: dict):
        async with self._pool.acquire() as conn:
            await conn.execute("""UPDATE {self._schema_name}.actor
                                  SET payload = $2
                                  WHERE username = $1""",
                               username,
                               payload)

    async def delete(self, username: str, _=None):
        async with self._pool.acquire() as conn:
            await conn.execute("""DELETE FROM {self._schema_name}.actor
                                  WHERE username = $1""",
                               username)

    async def fetch(self, username: str):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT payload
                                         FROM {self._schema_name}.actor
                                         WHERE username = $1""",
                                      username)
        return row["payload"] if row is not None else None


_instance: _storage | None = None


async def init(component_name: str, config: Dict[str, str]) -> None:
    global _instance
    pool = await create_pool(host=config["host"],
                             port=int(config["port"]),
                             database=config["database"],
                             user=config["user"],
                             password=config["password"],)
    _instance = _storage(pool, component_name)


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Actor storage is not initialized.")
    return _instance

