# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.bookmarks
                                    (actor_url  TEXT   NOT NULL,
                                     object_url TEXT   NOT NULL,
                                     marked_at  BIGINT NOT NULL,
                                     PRIMARY KEY (actor_url, object_url))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS bookmarks_of_an_actor
                              ON api.bookmarks (actor_url, marked_at DESC)""")

    async def add(self, actor_url: str, object_url: str, marked_at: int) -> None:
        await self.execute("""INSERT INTO
                                  api.bookmarks
                                      (actor_url, object_url, marked_at)
                              VALUES
                                  ($1, $2, $3)
                              ON CONFLICT (actor_url, object_url) DO NOTHING""",
                           actor_url,
                           object_url,
                           marked_at)

    async def remove(self, actor_url: str, object_url: str) -> None:
        await self.execute("""DELETE FROM
                                  api.bookmarks
                              WHERE
                                  actor_url = $1 AND
                                  object_url = $2""",
                           actor_url,
                           object_url)

    async def page(self, actor_url: str, limit: int, max_id: Optional[str], since_id: Optional[str]) -> list:
        return await self.fetch_all("""
            SELECT
                object_url,
                marked_at
            FROM
                api.bookmarks
            WHERE
                actor_url = $1 AND
                ($3::bigint IS NULL OR marked_at < $3::bigint) AND
                ($4::bigint IS NULL OR marked_at > $4::bigint)
            ORDER BY
                marked_at DESC
            LIMIT $2""",
                                    actor_url,
                                    limit,
                                    max_id,
                                    since_id)

    async def marked(self, object_urls: list[str], actor_url: Optional[str]) -> set:
        return {row["object_url"] for row in await self.fetch_all("""
            SELECT
                object_url
            FROM
                api.bookmarks
            WHERE
                actor_url = $1 AND
                object_url = ANY($2::text[])""",
                                                                  actor_url,
                                                                  object_urls)} if actor_url else set()


_instance: Optional[_storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("bookmarks storage is not initialized.")
    return _instance

