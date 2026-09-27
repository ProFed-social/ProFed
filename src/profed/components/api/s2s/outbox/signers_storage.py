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
                              api.s2s_outbox_signers
                                 (actor_url      TEXT        PRIMARY KEY,
                                  actor_type     TEXT        NOT NULL,
                                  public_key_pem TEXT        NOT NULL,
                                  fetched_at     TIMESTAMPTZ NOT NULL)""")

    async def upsert(self,
                     actor_url:      str,
                     actor_type:     str,
                     public_key_pem: str,
                     fetched_at:     datetime) -> None:
        await self.execute("""INSERT INTO api.s2s_outbox_signers
                                          (actor_url,
                                           actor_type,
                                           public_key_pem,
                                           fetched_at)
                              VALUES ($1, $2, $3, $4)
                              ON CONFLICT (actor_url) DO UPDATE
                                  SET actor_type     = EXCLUDED.actor_type,
                                      public_key_pem = EXCLUDED.public_key_pem,
                                      fetched_at     = EXCLUDED.fetched_at""",
                           actor_url, actor_type, public_key_pem, fetched_at)

    async def signer(self, actor_url: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT actor_url,
                                              actor_type,
                                              public_key_pem,
                                              fetched_at
                                       FROM api.s2s_outbox_signers
                                       WHERE actor_url = $1""",
                                    actor_url)


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("s2s outbox signers storage not initialized")
    return _instance

