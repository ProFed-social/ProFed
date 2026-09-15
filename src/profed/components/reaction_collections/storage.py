# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE SCHEMA IF NOT EXISTS reaction_collections""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              reaction_collections.collection
                                    (object_url     TEXT NOT NULL,
                                     collection_url TEXT NOT NULL,
                                     PRIMARY KEY (object_url))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              reaction_collections.inspection
                                    (object_url  TEXT        NOT NULL,
                                     state       TEXT        NOT NULL,
                                     checked_at  TIMESTAMPTZ NOT NULL,
                                     next_due_at TIMESTAMPTZ NOT NULL,
                                     attempt     INT         NOT NULL DEFAULT 0,
                                     PRIMARY KEY (object_url))""")

    async def remember(self, object_url: str, collection_url: str) -> None:
        await self.execute("""INSERT INTO
                                  reaction_collections.collection
                                      (object_url, collection_url)
                              VALUES
                                  ($1, $2)
                              ON CONFLICT (object_url) DO UPDATE
                                  SET
                                      collection_url = EXCLUDED.collection_url""",
                           object_url,
                           collection_url)

    async def forget(self, object_url: str) -> None:
        await self.execute("""DELETE FROM
                                  reaction_collections.collection
                              WHERE
                                  object_url = $1""",
                           object_url)

    async def due(self, object_urls: list, now: datetime, lease: timedelta) -> list:
        return await self.fetch_all("""
            SELECT
                c.object_url,
                c.collection_url,
                COALESCE(i.attempt, 0) AS attempt
            FROM
                reaction_collections.collection AS c LEFT JOIN
                reaction_collections.inspection AS i ON i.object_url = c.object_url
            WHERE
                c.object_url = ANY($1::text[]) AND
                (i.object_url IS NULL OR
                 (i.state = 'attempting' AND i.checked_at < $2 - $3) OR
                 (i.state <> 'attempting' AND i.next_due_at <= $2))""",
                                    object_urls,
                                    now,
                                    lease)

    async def record(self,
                     object_url: str,
                     state: str,
                     checked_at: datetime,
                     next_due_at: Optional[datetime],
                     attempt: int) -> None:
        await self.execute("""INSERT INTO
                                  reaction_collections.inspection
                                      (object_url, state, checked_at, next_due_at, attempt)
                              VALUES
                                  ($1, $2, $3, COALESCE($4, $3), $5)
                              ON CONFLICT (object_url) DO UPDATE
                                  SET
                                      state = EXCLUDED.state,
                                      checked_at = EXCLUDED.checked_at,
                                      next_due_at = EXCLUDED.next_due_at,
                                      attempt = EXCLUDED.attempt
                                  WHERE
                                      reaction_collections.inspection.checked_at <= EXCLUDED.checked_at""",
                           object_url,
                           state,
                           checked_at,
                           next_due_at,
                           attempt)


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("reaction_collections storage not initialised")
    return _instance

