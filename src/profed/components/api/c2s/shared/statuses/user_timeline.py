# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.user_timeline
                                    (username   TEXT NOT NULL,
                                     object_url TEXT NOT NULL,
                                     PRIMARY KEY (username, object_url))""")

    async def add(self, username: str, object_url: str) -> None:
        await self.execute("""INSERT INTO api.user_timeline
                                          (username, object_url)
                              VALUES ($1, $2)
                              ON CONFLICT (username, object_url) DO NOTHING""",
                           username,
                           object_url)

    async def remove(self, username: str, object_url: str) -> None:
        await self.execute("""DELETE FROM api.user_timeline
                              WHERE username = $1 AND object_url = $2""",
                           username,
                           object_url)

    async def remove_object(self, object_url: str) -> None:
        await self.execute("""DELETE FROM api.user_timeline
                              WHERE object_url = $1""",
                           object_url)

    async def fetch(self,
                    username: str,
                    limit: int = 20,
                    max_id: Optional[str] = None,
                    since_id: Optional[str] = None) -> List[dict]:
        return await self.fetch_all("""SELECT o.mastodon_id, o.url, o.actor_url, o.kind, o.status, r.content
                                       FROM api.as_objects o
                                       JOIN api.user_timeline ut ON ut.object_url = o.url
                                       CROSS JOIN LATERAL
                                            (SELECT api.resolve_content(o.url) AS content) r
                                       WHERE ut.username = $1
                                         AND ($3::numeric IS NULL OR o.mastodon_id < $3::numeric)
                                         AND ($4::numeric IS NULL OR o.mastodon_id > $4::numeric)
                                         AND r.content IS NOT NULL
                                       ORDER BY o.mastodon_id DESC
                                       LIMIT $2""",
                                    username,
                                    limit,
                                    max_id,
                                    since_id)

    def thread_roots(self, username: str, max_depth: int = 20):
        return self.stream("""SELECT o.mastodon_id,
                                     api.thread_root(api.content_url(o.url), $2) AS root,
                                     CASE WHEN o.kind = 'announce' THEN o.actor_url END AS booster
                              FROM api.as_objects o
                              JOIN api.user_timeline ut ON ut.object_url = o.url
                              WHERE ut.username = $1
                              ORDER BY o.mastodon_id DESC""",
                           username,
                           max_depth)


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("user_timeline storage is not initialized.")
    return _instance

