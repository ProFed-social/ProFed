# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              polish_activities.local_accounts
                                    (username TEXT PRIMARY KEY)""")

    async def add(self, username: str) -> None:
        await self.execute("""INSERT INTO polish_activities.local_accounts (username)
                              VALUES ($1)
                              ON CONFLICT (username) DO NOTHING""",
                           username)

    async def delete(self, username: str) -> None:
        await self.execute("""DELETE FROM polish_activities.local_accounts
                              WHERE username = $1""",
                           username)

    async def exists(self, username: str) -> bool:
        row = await self.fetch_one("""SELECT 1
                                      FROM polish_activities.local_accounts
                                      WHERE username = $1""",
                                   username)
        return row is not None


_instance: _Storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("Polish activities storage is not initialized.")
    return _instance

