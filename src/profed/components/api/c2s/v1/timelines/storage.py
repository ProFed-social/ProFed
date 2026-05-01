# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_home_timeline"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.c2s_home_timeline
                                    (id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                                     username   TEXT        NOT NULL,
                                     created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                     activity   JSONB       NOT NULL)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              c2s_home_timeline_username_idx
                              ON api.c2s_home_timeline (username,
                                                        created_at DESC)""")

    async def add(self, username: str, activity: dict) -> None:
        await self.execute("""INSERT INTO api.c2s_home_timeline (username, activity)
                              VALUES ($1, $2)""",
                           username,
                           activity)

    async def fetch(self,
                    username: str,
                    limit: int = 20,
                    max_id: Optional[str] = None,
                    since_id: Optional[str] = None) -> List[tuple[str, dict]]:
        rows = await self.fetch_all("""SELECT id::text, activity
                                       FROM api.c2s_home_timeline
                                       WHERE username = $1
                                       ORDER BY created_at DESC
                                       LIMIT $2""",
                                    username,
                                    limit)
        return [(row["id"], row["activity"]) for row in rows]


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Home timeline storage is not initialized.")
    return _instance
