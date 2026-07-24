# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.c2s_home_timeline
                                    (username    TEXT    NOT NULL,
                                     status_id   TEXT    NOT NULL,
                                     mastodon_id NUMERIC NOT NULL,
                                     actor_url   TEXT    NOT NULL,
                                     status      JSONB   NOT NULL,
                                     PRIMARY KEY (username, status_id))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              c2s_home_timeline_username_mastodon_idx
                              ON api.c2s_home_timeline (username,
                                                        mastodon_id DESC)""")

    async def add(self, username: str, status_id: str, mastodon_id: str, actor_url: str, status: dict) -> None:
        await self.execute("""INSERT INTO api.c2s_home_timeline
                                          (username, status_id, mastodon_id, actor_url, status)
                              VALUES ($1, $2, $3::numeric, $4, $5)
                              ON CONFLICT (username, status_id) DO NOTHING""",
                           username,
                           status_id,
                           mastodon_id,
                           actor_url,
                           status)

    async def update_status(self, username: str, status_id: str, status: dict) -> None:
        await self.execute("""UPDATE api.c2s_home_timeline
                              SET status = $3
                              WHERE username = $1 AND status_id = $2""",
                           username,
                           status_id,
                           status)

    async def delete_status(self, username: str, status_id: str) -> None:
        await self.execute("""DELETE FROM api.c2s_home_timeline
                              WHERE username = $1 AND status_id = $2""",
                           username,
                           status_id)

    async def fetch(self,
                    username: str,
                    limit: int = 20,
                    max_id: Optional[str] = None,
                    since_id: Optional[str] = None) -> List[tuple[str, dict]]:
        rows = await self.fetch_all("""SELECT actor_url, status
                                       FROM api.c2s_home_timeline
                                       WHERE username = $1
                                         AND ($3::numeric IS NULL OR mastodon_id < $3::numeric)
                                         AND ($4::numeric IS NULL OR mastodon_id > $4::numeric)
                                       ORDER BY mastodon_id DESC
                                       LIMIT $2""",
                                    username,
                                    limit,
                                    max_id,
                                    since_id)
        return [(row["actor_url"], row["status"]) for row in rows]

    async def get_by_id(self, username: str, mastodon_id: str) -> tuple[str, dict] | None:
        row = await self.fetch_one("""SELECT actor_url, status
                                      FROM api.c2s_home_timeline
                                      WHERE username = $1 AND mastodon_id = $2::numeric""",
                                   username,
                                   mastodon_id)
        return (row["actor_url"], row["status"]) if row else None


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("Home timeline storage is not initialized.")
    return _instance

