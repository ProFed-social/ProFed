# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None)

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.s2s_outbox (username   TEXT        NOT NULL,
                                              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                              activity   JSONB       NOT NULL)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              outbox_username_created_at_idx
                              ON api.s2s_outbox (username,
                                                 created_at)""")

    async def add(self, username: str, activity: dict) -> None:
        await self.execute("""INSERT INTO api.s2s_outbox (username, activity)
                              VALUES ($1, $2)""",
                           username,
                           activity)

    async def fetch(self, username: str) -> List[dict]:
        rows = await self.fetch_all("""SELECT activity
                                       FROM api.s2s_outbox
                                       WHERE username = $1
                                       ORDER BY created_at""",
                                    username)
        return [row["activity"] for row in rows]


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Outbox storage is not initialized.")
    return _instance
