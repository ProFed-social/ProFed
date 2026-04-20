# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Optional
from asyncpg import Pool, create_pool
import json


class _storage:
    def __init__(self, pool: Pool):
        self._pool = pool

    async def ensure_table(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS api.s2s_actor (
                                      username TEXT PRIMARY KEY,
                                      payload JSONB NOT NULL)""")

    async def add(self, username: str, payload: dict):
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO api.s2s_actor (username, payload)
                                  VALUES ($1, $2)""",
                               username,
                               json.dumps(payload))

    async def update(self, username: str, payload: dict):
        async with self._pool.acquire() as conn:
            await conn.execute("""UPDATE api.s2s_actor
                                  SET payload = $2
                                  WHERE username = $1""",
                               username,
                               json.dumps(payload))

    async def delete(self, username: str, _=None):
        async with self._pool.acquire() as conn:
            await conn.execute("""DELETE FROM api.s2s_actor
                                  WHERE username = $1""",
                               username)

    async def fetch(self, username: str) -> Optional[Dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT payload
                                         FROM api.s2s_actor
                                         WHERE username = $1""",
                                      username)
        return json.loads(row["payload"]) if row is not None else None


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    pool = await create_pool(host=config["host"],
                             port=int(config["port"]),
                             database=config["database"],
                             user=config["user"],
                             password=config["password"],)
    _instance = _storage(pool)


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Actor storage is not initialized.")
    return _instance

