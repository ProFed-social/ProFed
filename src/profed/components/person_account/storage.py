# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None)

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              person_account.edges (follower TEXT NOT NULL,
                                                    following TEXT NOT NULL,
                                                    PRIMARY KEY (follower, following))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              person_account.statuses (username TEXT NOT NULL,
                                                       status_id TEXT NOT NULL,
                                                       PRIMARY KEY (username, status_id))""")

    async def add_edge(self, follower: str, following: str) -> bool:
        row = await self.fetch_one("""INSERT INTO person_account.edges (follower, following)
                                      VALUES ($1, $2)
                                      ON CONFLICT DO NOTHING
                                      RETURNING follower""",
                                   follower,
                                   following)
        return row is not None

    async def remove_edge(self, follower: str, following: str) -> bool:
        row = await self.fetch_one("""DELETE FROM person_account.edges
                                      WHERE follower = $1 AND following = $2
                                      RETURNING follower""",
                                   follower,
                                   following)
        return row is not None

    async def count_followers(self, acct: str) -> int:
        row = await self.fetch_one("""SELECT COUNT(*) AS count
                                      FROM person_account.edges
                                      WHERE following = $1""",
                                   acct)
        return row["count"]

    async def count_following(self, acct: str) -> int:
        row = await self.fetch_one("""SELECT COUNT(*) AS count
                                      FROM person_account.edges
                                      WHERE follower = $1""",
                                   acct)
        return row["count"]

    async def count_follows(self, acct: str) -> tuple[int, int]:
        row = await self.fetch_one("""SELECT COUNT(*) FILTER (WHERE following = $1) AS followers,
                                             COUNT(*) FILTER (WHERE follower = $1) AS following
                                      FROM person_account.edges
                                      WHERE follower = $1 OR following = $1""",
                                   acct)
        return (row["followers"], row["following"]) if row else (0, 0)

    async def add_status(self, username: str, status_id: str) -> bool:
        row = await self.fetch_one("""INSERT INTO person_account.statuses (username, status_id)
                                      VALUES ($1, $2)
                                      ON CONFLICT DO NOTHING
                                      RETURNING username""",
                                   username,
                                   status_id)
        return row is not None

    async def remove_status(self, username: str, status_id: str) -> bool:
        row = await self.fetch_one("""DELETE FROM person_account.statuses
                                      WHERE username = $1 AND status_id = $2
                                      RETURNING username""",
                                   username,
                                   status_id)
        return row is not None

    async def count_statuses(self, username: str) -> int:
        row = await self.fetch_one("""SELECT COUNT(*) AS count
                                      FROM person_account.statuses
                                      WHERE username = $1""",
                                   username)
        return row["count"]


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("person_account storage not initialised")
    return _instance

