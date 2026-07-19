# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              delivery_splitter.follower_history
                                    (following TEXT      NOT NULL,
                                     follower  TEXT      NOT NULL,
                                     valid     TSTZRANGE NOT NULL,
                                     PRIMARY KEY (following, follower))""")

    async def accept_edge(self, following: str, follower: str, at) -> None:
        await self.execute("""INSERT INTO delivery_splitter.follower_history
                                    (following, follower, valid)
                              VALUES ($1, $2, tstzrange($3, 'infinity'::timestamptz))
                              ON CONFLICT (following, follower) DO UPDATE
                                  SET valid = tstzrange($3, 'infinity'::timestamptz)""",
                           following,
                           follower,
                           at)

    async def delete_edge(self, following: str, follower: str, at) -> None:
        await self.execute("""UPDATE delivery_splitter.follower_history
                              SET valid = tstzrange(lower(valid), $3)
                              WHERE following = $1 AND follower = $2""",
                           following,
                           follower,
                           at)

    async def recipients_at(self, following: str, at) -> set[str]:
        rows = await self.fetch_all("""SELECT follower
                                       FROM delivery_splitter.follower_history
                                       WHERE following = $1
                                         AND valid @> $2::timestamptz""",
                                    following,
                                    at)
        return {row["follower"] for row in rows}


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("delivery_splitter storage not initialized")
    return _instance

