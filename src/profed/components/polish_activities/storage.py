# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              polish_activities.known_accounts
                                    (account_id BIGINT PRIMARY KEY,
                                     acct       TEXT   UNIQUE NOT NULL,
                                     actor_url  TEXT   NOT NULL)""")

    async def upsert(self, account_id: int, acct: str, actor_url: str) -> None:
        await self.execute("""INSERT INTO polish_activities.known_accounts
                                    (account_id, acct, actor_url)
                              VALUES ($1, $2, $3)
                              ON CONFLICT (account_id) DO UPDATE
                                  SET acct      = EXCLUDED.acct,
                                      actor_url = EXCLUDED.actor_url""",
                           account_id,
                           acct,
                           actor_url)

    async def delete(self, account_id: int) -> None:
        await self.execute("""DELETE FROM polish_activities.known_accounts
                              WHERE account_id = $1""",
                           account_id)

    async def url_for(self, acct: str) -> Optional[str]:
        row = await self.fetch_one("""SELECT actor_url
                                      FROM polish_activities.known_accounts
                                      WHERE acct = $1""",
                                   acct)
        return row["actor_url"] if row is not None else None


_instance: _Storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("Polish activities storage is not initialized.")
    return _instance

