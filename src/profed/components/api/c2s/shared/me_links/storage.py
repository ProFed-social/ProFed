# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.me_links (actor_url  TEXT        NOT NULL,
                                            link_url   TEXT        NOT NULL,
                                            state      TEXT        NOT NULL,
                                            checked_at TIMESTAMPTZ NOT NULL,
                                            PRIMARY KEY (actor_url, link_url))""")
        await self.execute("""CREATE OR REPLACE VIEW api.me_link_entry AS
                              SELECT actor_url,
                                     link_url,
                                     jsonb_build_object('state', state, 'checked_at', checked_at) AS entry
                              FROM api.me_links""")

    async def upsert(self, actor_url: str, link_url: str, state: str, checked_at) -> None:
        await self.execute("""INSERT INTO api.me_links (actor_url, link_url, state, checked_at)
                              VALUES ($1, $2, $3, $4)
                              ON CONFLICT (actor_url, link_url) DO UPDATE
                                  SET state = EXCLUDED.state,
                                      checked_at = EXCLUDED.checked_at""",
                           actor_url,
                           link_url,
                           state,
                           checked_at)

    async def delete(self, actor_url: str, link_url: str) -> None:
        await self.execute("""DELETE FROM api.me_links
                              WHERE actor_url = $1 AND link_url = $2""",
                           actor_url,
                           link_url)


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("api me_links storage not initialised")
    return _instance

