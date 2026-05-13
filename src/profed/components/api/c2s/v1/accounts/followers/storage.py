# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_c2s_followers"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.c2s_followers (following TEXT NOT NULL,
                                                 follower  TEXT NOT NULL,
                                                 PRIMARY KEY (following, follower))""")

    async def add_follower(self,
                           following: str,
                           follower:  str) -> None:
        await self.execute("""INSERT INTO api.c2s_followers (following, follower)
                              VALUES ($1, $2)
                              ON CONFLICT DO NOTHING""",
                           following,
                           follower)

    async def remove_follower(self,
                              following: str,
                              follower:  str) -> None:
        await self.execute("""DELETE FROM api.c2s_followers
                              WHERE following = $1 AND follower = $2""",
                           following,
                           follower)

    async def get_followers(self, following: str) -> list[str]:
        rows = await self.fetch_all("""SELECT follower
                                       FROM api.c2s_followers
                                       WHERE following = $1""",
                                    following)

        return [row["follower"] for row in rows]


_instance: _storage | None = None


async def init(config: dict) -> None:
    global _instance
    pool = await init_pool(config)
    _instance = _storage(pool)
    await _instance.ensure_schema()


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("followers storage not initialised")
    return _instance

