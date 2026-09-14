# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.known_servers (host       TEXT  PRIMARY KEY,
                                                 reacted_at TIMESTAMPTZ,
                                                 software   TEXT,
                                                 features   JSONB NOT NULL DEFAULT '[]'::jsonb,
                                                 checked_at TIMESTAMPTZ)""")

    async def support_of(self, host: str) -> Optional[bool]:
        row = await self.fetch_one("""SELECT (reacted_at IS NOT NULL OR
                                              features ? 'pleroma_emoji_reactions') AS supported
                                      FROM api.known_servers
                                      WHERE host = $1""",
                                   host)
        return None if row is None else row["supported"]

    async def record_observation(self, host: str, observed_at) -> None:
        await self.execute("""INSERT INTO api.known_servers (host, reacted_at)
                              VALUES ($1, $2)
                              ON CONFLICT (host) DO UPDATE
                                  SET reacted_at = GREATEST(api.known_servers.reacted_at, EXCLUDED.reacted_at)""",
                           host,
                           observed_at)

    async def record_update(self, host: str, software, features, checked_at) -> None:
        await self.execute("""INSERT INTO api.known_servers (host, software, features, checked_at)
                              VALUES ($1, $2, $3::jsonb, $4)
                              ON CONFLICT (host) DO UPDATE
                                  SET software   = EXCLUDED.software,
                                      features   = EXCLUDED.features,
                                      checked_at = EXCLUDED.checked_at""",
                           host,
                           software,
                           json.dumps(features),
                           checked_at)


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("api known_servers storage not initialised")
    return _instance

