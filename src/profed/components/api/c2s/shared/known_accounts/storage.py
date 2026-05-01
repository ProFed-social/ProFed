# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_c2s_known_accounts"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.known_accounts (account_id        BIGINT      PRIMARY KEY,
                                                  acct              TEXT        UNIQUE NOT NULL,
                                                  actor_url         TEXT        UNIQUE NOT NULL,
                                                  actor_data        JSONB,
                                                  last_webfinger_at TIMESTAMPTZ NOT NULL)""")

    async def upsert(self,
                     account_id: int,
                     acct: str,
                     actor_url: str,
                     actor_data: dict | None,
                     last_webfinger_at: datetime) -> None:
        await self.execute("""INSERT INTO
                              api.known_accounts (account_id,
                                                  acct,
                                                  actor_url,
                                                  actor_data,
                                                  last_webfinger_at)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (account_id) DO UPDATE
                                  SET acct              = EXCLUDED.acct,
                                      actor_url         = EXCLUDED.actor_url,
                                      actor_data        = EXCLUDED.actor_data,
                                      last_webfinger_at = EXCLUDED.last_webfinger_at""",
                           account_id,
                           acct,
                           actor_url,
                           actor_data,
                           last_webfinger_at)

    async def get_by_id(self, account_id: int) -> Optional[dict]:
        return await self.fetch_one("""SELECT account_id,
                                              acct,
                                              actor_url,
                                              actor_data,
                                              last_webfinger_at
                                        FROM api.known_accounts
                                        WHERE account_id = $1""",
                                    account_id)

    async def get_by_acct(self, acct: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT account_id,
                                              acct,
                                              actor_url,
                                              actor_data,
                                              last_webfinger_at
                                       FROM api.known_accounts
                                       WHERE acct = $1""",
                                    acct)

    async def get_by_actor_url(self, actor_url: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT account_id,
                                              acct,
                                              actor_url,
                                              actor_data,
                                              last_webfinger_at
                                       FROM api.known_accounts
                                       WHERE actor_url = $1""",
                                    actor_url)


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("known_accounts storage not initialized")
    return _instance

