# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.reaction_formats (reaction_url TEXT NOT NULL,
                                                    verb         TEXT NOT NULL,
                                                    PRIMARY KEY (reaction_url))""")

    async def remember(self, reaction_url: str, verb: str) -> None:
        await self.execute("""INSERT INTO api.reaction_formats (reaction_url, verb)
                              VALUES ($1, $2)
                              ON CONFLICT (reaction_url) DO UPDATE SET verb = EXCLUDED.verb""",
                           reaction_url,
                           verb)

    async def forget(self, reaction_url: str) -> None:
        await self.execute("""DELETE FROM api.reaction_formats WHERE reaction_url = $1""", reaction_url)

    async def verb_of(self, reaction_url: str) -> Optional[str]:
        row = await self.fetch_one("""SELECT verb FROM api.reaction_formats WHERE reaction_url = $1""",
                                   reaction_url)
        return None if row is None else row["verb"]


_instance: Optional[_Storage] = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("v1 pleroma reaction format storage not initialised")
    return _instance

