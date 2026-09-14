# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              known_servers.host (host TEXT NOT NULL,
                                                  PRIMARY KEY (host))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              known_servers.inspection
                                    (host          TEXT        NOT NULL,
                                     checked_at    TIMESTAMPTZ NOT NULL,
                                     stable_since  TIMESTAMPTZ NOT NULL,
                                     next_due_at   TIMESTAMPTZ NOT NULL,
                                     failures      INTEGER     NOT NULL DEFAULT 0,
                                     last_modified TEXT,
                                     etag          TEXT,
                                     content_hash  TEXT,
                                     PRIMARY KEY (host))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS inspection_due
                              ON known_servers.inspection (next_due_at)""")

    async def remember_host(self, host: str) -> None:
        await self.execute("""INSERT INTO known_servers.host (host)
                              VALUES ($1)
                              ON CONFLICT (host) DO NOTHING""",
                           host)

    async def forget_host(self, host: str) -> None:
        await self.execute("""DELETE FROM known_servers.host WHERE host = $1""", host)

    async def record_check(self,
                           host: str,
                           checked_at,
                           stable_since,
                           next_due_at,
                           failures: int,
                           last_modified: Optional[str],
                           etag: Optional[str],
                           content_hash: Optional[str]) -> None:
        await self.execute("""INSERT INTO known_servers.inspection
                                    (host, checked_at, stable_since, next_due_at,
                                     failures, last_modified, etag, content_hash)
                              VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                              ON CONFLICT (host) DO UPDATE
                                  SET checked_at    = EXCLUDED.checked_at,
                                      stable_since  = EXCLUDED.stable_since,
                                      next_due_at   = EXCLUDED.next_due_at,
                                      failures      = EXCLUDED.failures,
                                      last_modified = EXCLUDED.last_modified,
                                      etag          = EXCLUDED.etag,
                                      content_hash  = EXCLUDED.content_hash""",
                           host,
                           checked_at,
                           stable_since,
                           next_due_at,
                           failures,
                           last_modified,
                           etag,
                           content_hash)

    async def check_of(self, host: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT host, checked_at, stable_since, next_due_at,
                                              failures, last_modified, etag, content_hash
                                       FROM known_servers.inspection
                                       WHERE host = $1""",
                                    host)

    async def unchecked(self) -> List[dict]:
        return await self.fetch_all("""SELECT h.host
                                       FROM known_servers.host AS h
                                       LEFT JOIN known_servers.inspection AS c ON c.host = h.host
                                       WHERE c.host IS NULL""")

    async def due(self, now) -> List[dict]:
        return await self.fetch_all("""SELECT c.host
                                       FROM known_servers.inspection AS c
                                       INNER JOIN known_servers.host AS h ON h.host = c.host
                                       WHERE c.next_due_at <= $1""",
                                    now)


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("known_servers storage not initialised")
    return _instance

