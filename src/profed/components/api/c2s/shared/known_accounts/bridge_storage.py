# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_c2s_known_local"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS api.c2s_known_local
                              (username   TEXT        PRIMARY KEY,
                               created_at TIMESTAMPTZ NOT NULL,
                               profile    JSONB       NOT NULL)""")

    async def upsert_created(self, username: str, profile: dict, created_at: datetime) -> None:
        await self.execute("""INSERT INTO api.c2s_known_local (username, created_at, profile)
                              VALUES ($1, $2, $3)
                              ON CONFLICT (username) DO UPDATE
                                  SET created_at = $2,
                                      profile    = $3""",
                           username,
                           created_at,
                           profile)

    async def merge_change(self, username: str, partial: dict) -> None:
        await self.execute("""UPDATE api.c2s_known_local
                              SET profile = profile || $2
                              WHERE username = $1""",
                           username,
                           partial)

    async def delete(self, username: str) -> None:
        await self.execute("""DELETE FROM api.c2s_known_local
                              WHERE username = $1""",
                           username)

    async def fetch(self, username: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT username, created_at, profile
                                       FROM api.c2s_known_local
                                       WHERE username = $1""",
                                    username)


_instance: _storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Known-accounts local bridge storage is not initialized.")
    return _instance
