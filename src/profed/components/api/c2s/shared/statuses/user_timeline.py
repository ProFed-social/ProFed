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
                                    (username    TEXT    NOT NULL,
                                     object_url  TEXT    NOT NULL,
                                     mastodon_id NUMERIC NOT NULL,
                                     PRIMARY KEY (username, object_url))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              user_timeline_username_mastodon_idx
                              ON api.user_timeline (username,
                                                    mastodon_id DESC)""")

    async def add(self, username: str, object_url: str, mastodon_id: str) -> None:
        await self.execute("""INSERT INTO api.user_timeline
                                          (username, object_url, mastodon_id)
                              VALUES ($1, $2, $3::numeric)
                              ON CONFLICT (username, object_url) DO NOTHING""",
                           username,
                           object_url,
                           mastodon_id)

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
        return await self.fetch_all("""SELECT ut.mastodon_id, o.url, o.actor_url, o.reblog_of_url, o.status, r.content
                                       FROM api.user_timeline ut
                                       JOIN api.as_objects o ON o.url = ut.object_url
                                       CROSS JOIN LATERAL
                                            (SELECT api.resolve_content(o.url) AS content) r
                                       WHERE ut.username = $1
                                         AND ($3::numeric IS NULL OR ut.mastodon_id < $3::numeric)
                                         AND ($4::numeric IS NULL OR ut.mastodon_id > $4::numeric)
                                         AND r.content IS NOT NULL
                                       ORDER BY ut.mastodon_id DESC
                                       LIMIT $2""",
                                    username,
                                    limit,
                                    max_id,
                                    since_id)

    def thread_roots(self, username: str, max_depth: int = 20):
        return self.stream("""SELECT ut.mastodon_id,
                                     api.thread_root(api.content_url(o.url), $2) AS root,
                                     CASE WHEN o.reblog_of_url IS NOT NULL THEN o.actor_url END AS booster
                              FROM api.user_timeline ut
                              JOIN api.as_objects o ON o.url = ut.object_url
                              WHERE ut.username = $1
                              ORDER BY ut.mastodon_id DESC""",
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

