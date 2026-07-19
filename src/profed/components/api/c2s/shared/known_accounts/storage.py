# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.known_accounts (account_id        BIGINT      PRIMARY KEY,
                                                  acct              TEXT        UNIQUE NOT NULL,
                                                  acct_local        TEXT        NOT NULL,
                                                  actor_url         TEXT        UNIQUE NOT NULL,
                                                  account           JSONB       NOT NULL,
                                                  last_webfinger_at TIMESTAMPTZ NOT NULL)""")

    async def upsert(self,
                     account_id: int,
                     acct: str,
                     actor_url: str,
                     account: dict,
                     last_webfinger_at: datetime) -> None:
        await self.execute("""INSERT INTO
                              api.known_accounts (account_id,
                                                  acct,
                                                  acct_local,
                                                  actor_url,
                                                  account,
                                                  last_webfinger_at)
                              VALUES ($1, $2, split_part($2, '@', 1), $3, $4, $5)
                              ON CONFLICT (account_id) DO UPDATE
                                  SET acct              = EXCLUDED.acct,
                                      acct_local        = EXCLUDED.acct_local,
                                      actor_url         = EXCLUDED.actor_url,
                                      account           = jsonb_set(EXCLUDED.account,
                                                                    '{created_at}',
                                                                    COALESCE(known_accounts.account -> 'created_at',
                                                                             EXCLUDED.account -> 'created_at')),
                                      last_webfinger_at = EXCLUDED.last_webfinger_at""",
                           account_id,
                           acct,
                           actor_url,
                           account,
                           last_webfinger_at)

    async def update(self, account_id: int, patch: dict) -> None:
        await self.execute("""UPDATE api.known_accounts
                              SET account = account || $2
                              WHERE account_id = $1""",
                           account_id,
                           patch)

    async def delete(self, account_id: int) -> None:
        await self.execute("""DELETE FROM api.known_accounts
                              WHERE account_id = $1""",
                           account_id)

    async def get_by_id(self, account_id: int) -> Optional[dict]:
        return await self.fetch_one("""SELECT account_id,
                                              acct,
                                              actor_url,
                                              account,
                                              last_webfinger_at
                                        FROM api.known_accounts
                                        WHERE account_id = $1""",
                                    account_id)

    async def get_by_acct(self, acct: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT account_id,
                                              acct,
                                              actor_url,
                                              account,
                                              last_webfinger_at
                                       FROM api.known_accounts
                                       WHERE acct = $1 OR acct_local = $1""",
                                    acct)

    async def get_by_actor_url(self, actor_url: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT account_id,
                                              acct,
                                              actor_url,
                                              account,
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

