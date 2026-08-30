# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              me_links.link
                                    (actor_url   TEXT NOT NULL,
                                     profile_url TEXT NOT NULL,
                                     link_url    TEXT NOT NULL,
                                     PRIMARY KEY (actor_url, link_url))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              me_links.verification
                                    (actor_url        TEXT        NOT NULL,
                                     link_url         TEXT        NOT NULL,
                                     state            TEXT        NOT NULL,
                                     checked_at       TIMESTAMPTZ NOT NULL,
                                     stable_since     TIMESTAMPTZ NOT NULL,
                                     next_due_at      TIMESTAMPTZ NOT NULL,
                                     last_modified    TEXT,
                                     etag             TEXT,
                                     content_hash     TEXT,
                                     PRIMARY KEY (actor_url, link_url))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS verification_due
                              ON me_links.verification (next_due_at)""")

    async def replace_links(self, actor_url: str, profile_url: str, link_urls: List[str]) -> None:
        await self.execute("""DELETE FROM me_links.link
                              WHERE actor_url = $1 AND link_url <> ALL($2)""",
                           actor_url,
                           link_urls)
        for link_url in link_urls:
            await self.execute("""INSERT INTO me_links.link (actor_url, profile_url, link_url)
                                  VALUES ($1, $2, $3)
                                  ON CONFLICT (actor_url, link_url) DO UPDATE
                                      SET profile_url = EXCLUDED.profile_url""",
                               actor_url,
                               profile_url,
                               link_url)

    async def forget_links(self, actor_url: str) -> None:
        await self.execute("""DELETE FROM me_links.link
                              WHERE actor_url = $1""",
                           actor_url)

    async def links_of(self, actor_url: str) -> List[str]:
        rows = await self.fetch_all("""SELECT link_url
                                       FROM me_links.link
                                       WHERE actor_url = $1""",
                                    actor_url)
        return [row["link_url"] for row in rows]

    async def record_verification(self,
                                  actor_url: str,
                                  link_url: str,
                                  state: str,
                                  checked_at,
                                  stable_since,
                                  next_due_at,
                                  last_modified: Optional[str],
                                  etag: Optional[str],
                                  content_hash: Optional[str]) -> None:
        await self.execute("""INSERT INTO me_links.verification
                                    (actor_url, link_url, state, checked_at, stable_since,
                                     next_due_at, last_modified, etag, content_hash)
                              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                              ON CONFLICT (actor_url, link_url) DO UPDATE
                                  SET state = EXCLUDED.state,
                                      checked_at = EXCLUDED.checked_at,
                                      stable_since = EXCLUDED.stable_since,
                                      next_due_at = EXCLUDED.next_due_at,
                                      last_modified = EXCLUDED.last_modified,
                                      etag = EXCLUDED.etag,
                                      content_hash = EXCLUDED.content_hash""",
                           actor_url,
                           link_url,
                           state,
                           checked_at,
                           stable_since,
                           next_due_at,
                           last_modified,
                           etag,
                           content_hash)

    async def forget_verification(self, actor_url: str, link_url: str) -> None:
        await self.execute("""DELETE FROM me_links.verification
                              WHERE actor_url = $1 AND link_url = $2""",
                           actor_url,
                           link_url)

    async def verification(self, actor_url: str, link_url: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT actor_url, link_url, state, checked_at, stable_since,
                                              next_due_at, last_modified, etag, content_hash
                                       FROM me_links.verification
                                       WHERE actor_url = $1 AND link_url = $2""",
                                    actor_url,
                                    link_url)

    async def unchecked(self) -> List[dict]:
        return await self.fetch_all("""SELECT l.actor_url, l.profile_url, l.link_url
                                       FROM me_links.link AS l
                                       LEFT JOIN me_links.verification AS v
                                              ON v.actor_url = l.actor_url
                                             AND v.link_url = l.link_url
                                       WHERE v.link_url IS NULL""")

    async def due(self, now) -> List[dict]:
        return await self.fetch_all("""SELECT v.actor_url, l.profile_url, v.link_url, v.state,
                                              l.link_url IS NOT NULL AS still_listed
                                       FROM me_links.verification AS v
                                       LEFT JOIN me_links.link AS l
                                              ON l.actor_url = v.actor_url
                                             AND l.link_url = v.link_url
                                       WHERE v.next_due_at <= $1""",
                                    now)


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("me_links storage not initialised")
    return _instance

