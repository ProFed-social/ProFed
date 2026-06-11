# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None)

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              person_account.edges (follower  TEXT NOT NULL,
                                                    following TEXT NOT NULL,
                                                    PRIMARY KEY (follower, following))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              person_account.statuses (username TEXT   PRIMARY KEY,
                                                       count    BIGINT NOT NULL DEFAULT 0)""")

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
        return row["count"] if row else 0

    async def count_following(self, acct: str) -> int:
        row = await self.fetch_one("""SELECT COUNT(*) AS count
                                      FROM person_account.edges
                                      WHERE follower = $1""",
                                   acct)
        return row["count"] if row else 0

    async def count_follows(self, acct: str) -> tuple[int, int]:
        row = await self.fetch_one("""SELECT
                                          COUNT(*) FILTER (WHERE following = $1) AS follower_count,
                                          COUNT(*) FILTER (WHERE follower = $1) AS following_count,
                                      FROM person_account.edges
                                      WHERE follower = $1 OR following = $1""",
                                   acct)
        return (row["follower_count"], row["following_count"]) if row else (0, 0)

    async def bump_statuses(self, username: str, delta: int) -> int:
        row = await self.fetch_one("""INSERT INTO person_account.statuses (username, count)
                                      VALUES ($1, GREATEST($2, 0))
                                      ON CONFLICT (username) DO UPDATE
                                          SET count = GREATEST(
                                                  person_account.statuses.count + $2, 0)
                                      RETURNING count""",
                                   username,
                                   delta)
        return row["count"] if row else 0

    async def get_statuses(self, username: str) -> int:
        row = await self.fetch_one("""SELECT count
                                      FROM person_account.statuses
                                     WHERE username = $1""",
                                   username)
        return row["count"] if row else 0


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("person_account storage not initialised")
    return _instance

