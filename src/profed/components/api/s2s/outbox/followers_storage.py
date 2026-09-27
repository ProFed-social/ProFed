# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.s2s_outbox_followers (following TEXT NOT NULL,
                                                        follower  TEXT NOT NULL,
                                                        PRIMARY KEY (following, follower))""")

    async def add_edge(self, following: str, follower: str) -> None:
        await self.execute("""INSERT INTO api.s2s_outbox_followers (following, follower)
                              VALUES ($1, $2)
                              ON CONFLICT DO NOTHING""",
                           following,
                           follower)

    async def drop_edge(self, following: str, follower: str) -> None:
        await self.execute("""DELETE FROM api.s2s_outbox_followers
                              WHERE following = $1
                                AND follower = $2""",
                           following,
                           follower)

    async def follows(self, following: str, followers: list[str], hosts: list[str]) -> bool:
        row = await self.fetch_one("""SELECT 1 AS found
                                      FROM api.s2s_outbox_followers
                                      WHERE following = $1
                                        AND (follower = ANY($2::text[])
                                             OR split_part(follower, '/', 3) = ANY($3::text[]))
                                      LIMIT 1""",
                                   following,
                                   followers,
                                   hosts)
        return row is not None


_instance: _Storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("s2s outbox followers storage not initialized")
    return _instance

