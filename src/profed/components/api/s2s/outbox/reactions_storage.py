# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.s2s_reactions (reaction_url TEXT   NOT NULL,
                                                 object_url   TEXT   NOT NULL,
                                                 actor_url    TEXT   NOT NULL,
                                                 emoji        TEXT   NOT NULL,
                                                 status_id    BIGINT NOT NULL,
                                                 PRIMARY KEY (reaction_url))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS s2s_reactions_of_object
                              ON api.s2s_reactions (object_url, status_id DESC)""")

    async def record(self, reaction_url: str, object_url: str, actor_url: str, emoji: str, status_id: int) -> None:
        await self.execute("""INSERT INTO api.s2s_reactions
                                    (reaction_url, object_url, actor_url, emoji, status_id)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (reaction_url) DO UPDATE
                                  SET object_url = EXCLUDED.object_url,
                                      actor_url  = EXCLUDED.actor_url,
                                      emoji      = EXCLUDED.emoji,
                                      status_id  = EXCLUDED.status_id""",
                           reaction_url,
                           object_url,
                           actor_url,
                           emoji,
                           status_id)

    async def forget(self, reaction_url: str) -> None:
        await self.execute("""DELETE FROM api.s2s_reactions WHERE reaction_url = $1""", reaction_url)

    async def count_for(self, object_url: str, emoji_only: bool = False) -> int:
        row = await self.fetch_one("""SELECT count(*) AS n
                                      FROM api.s2s_reactions
                                      WHERE object_url = $1 AND (NOT $2 OR emoji <> '')""",
                                   object_url,
                                   emoji_only)
        return 0 if row is None else row["n"]

    async def page(self, object_url: str, limit: int, before: Optional[int] = None, emoji_only: bool = False) \
            -> List[dict]:
        return await self.fetch_all("""SELECT reaction_url, actor_url, emoji, status_id
                                       FROM api.s2s_reactions
                                       WHERE object_url = $1
                                         AND ($2::BIGINT IS NULL OR status_id < $2)
                                         AND (NOT $3 OR emoji <> '')
                                       ORDER BY status_id DESC
                                       LIMIT $4""",
                                    object_url,
                                    before,
                                    emoji_only,
                                    limit)


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("s2s reactions storage not initialised")
    return _instance

