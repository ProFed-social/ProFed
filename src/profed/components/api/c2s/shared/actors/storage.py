# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_c2s_actor"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS api.c2s_actor (
                              username TEXT  PRIMARY KEY,
                              payload  JSONB NOT NULL)""")

    async def add(self, username: str, payload: dict) -> None:
        await self.execute("""INSERT INTO api.c2s_actor (username, payload)
                              VALUES ($1, $2)""",
                           username,
                           payload)

    async def update(self, username: str, payload: dict) -> None:
        await self.execute("""UPDATE api.c2s_actor
                              SET payload = $2
                              WHERE username = $1""",
                           username,
                           payload)

    async def delete(self, username: str) -> None:
        await self.execute("""DELETE FROM api.c2s_actor
                              WHERE username = $1""",
                           username)

    async def fetch(self, username: str) -> Optional[Dict]:
        row = await self.fetch_one("""SELECT payload
                                      FROM api.c2s_actor
                                      WHERE username = $1""",
                                   username)
        return row["payload"] if row is not None else None


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("C2S actor storage is not initialized.")
    return _instance
