# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_c2s_following"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.following (account_id     BIGINT  NOT NULL
                                                REFERENCES api.known_accounts (account_id),
                                             following_user TEXT    NOT NULL,
                                             accepted       BOOLEAN NOT NULL DEFAULT FALSE,
                                             PRIMARY KEY (account_id, following_user))""")

    async def upsert(self,
                     account_id: int,
                     following_user: str,
                     accepted: bool) -> None:
        await self.execute("""INSERT INTO api.following (account_id,
                                                         following_user,
                                                         accepted)
                              VALUES ($1, $2, $3)
                              ON CONFLICT (account_id, following_user) DO UPDATE
                                  SET accepted = EXCLUDED.accepted""",
                           account_id,
                           following_user,
                           accepted)

    async def delete(self,
                     account_id: int,
                     following_user: str) -> None:
        await self.execute("""DELETE FROM api.following
                              WHERE account_id = $1 AND following_user = $2""",
                           account_id,
                           following_user)

    async def get(self,
                  account_id: int,
                  following_user: str) -> dict | None:
        return await self.fetch_one("""SELECT account_id,
                                              following_user,
                                              accepted
                                       FROM api.following
                                       WHERE account_id = $1 AND following_user = $2""",
                                    account_id,
                                    following_user)


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("following storage not initialized")
    return _instance

