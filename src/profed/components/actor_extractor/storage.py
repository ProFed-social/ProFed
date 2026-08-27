# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              actor_extractor.known
                                    (actor_url TEXT PRIMARY KEY,
                                     acct      TEXT)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS known_acct
                              ON actor_extractor.known (acct)""")

    async def upsert(self, actor_url: str, acct: str | None) -> None:
        await self.execute("""INSERT INTO actor_extractor.known
                                    (actor_url, acct)
                              VALUES ($1, $2)
                              ON CONFLICT (actor_url) DO UPDATE
                                  SET acct = EXCLUDED.acct""",
                           actor_url,
                           acct)

    async def delete(self, actor_url: str) -> None:
        await self.execute("""DELETE FROM actor_extractor.known
                              WHERE actor_url = $1""",
                           actor_url)

    async def unknown_urls(self, urls: List[str]) -> List[str]:
        rows = await self.fetch_all("""SELECT url
                                       FROM unnest($1::text[]) AS url
                                       WHERE url NOT IN (SELECT actor_url FROM actor_extractor.known)""",
                                    urls)
        return [row["url"] for row in rows]

    async def unknown_accts(self, accts: List[str]) -> List[str]:
        rows = await self.fetch_all("""SELECT acct
                                       FROM unnest($1::text[]) AS acct
                                       WHERE acct NOT IN (SELECT k.acct
                                                          FROM actor_extractor.known AS k
                                                          WHERE k.acct IS NOT NULL)""",
                                    accts)
        return [row["acct"] for row in rows]


_instance: _Storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("Acct extractor storage is not initialized.")
    return _instance

