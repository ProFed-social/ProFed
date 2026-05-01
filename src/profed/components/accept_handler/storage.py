# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.base_storage import BaseStorage, init_pool
 
 
class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, "accept_handler")
 
    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS 
                              accept_handler.known_actor_ids (actor_url  TEXT   PRIMARY KEY,
                                                              account_id BIGINT NOT NULL)""")
 
    async def upsert(self, actor_url: str, account_id: int) -> None:
        await self.execute("""INSERT INTO
                              accept_handler.known_actor_ids (actor_url,
                                                              account_id)
                              VALUES ($1, $2)
                              ON CONFLICT (actor_url) DO UPDATE
                              SET account_id = EXCLUDED.account_id""",
                           actor_url,
                           account_id)
 
    async def get_by_actor_url(self, actor_url: str) -> int | None:
        row = await self.fetch_one("""SELECT account_id
                                      FROM accept_handler.known_actor_ids
                                      WHERE actor_url = $1""",
                                   actor_url)
        return row["account_id"] if row is not None else None
 
 
_instance: _Storage | None = None
 
 
async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))
 
 
async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("accept_handler storage not initialized")
    return _instance
 
