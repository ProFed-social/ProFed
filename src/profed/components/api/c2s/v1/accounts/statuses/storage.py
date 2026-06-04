# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_user_statuses"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.c2s_user_statuses
                                    (username    TEXT   NOT NULL,
                                     status_id   TEXT   NOT NULL,
                                     sequence_id BIGINT NOT NULL,
                                     activity    JSONB  NOT NULL,
                                     PRIMARY KEY (username, status_id))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              c2s_user_statuses_username_seq_idx
                              ON api.c2s_user_statuses (username,
                                                        sequence_id DESC)""")

    async def add(self,
                  username: str,
                  status_id: str,
                  sequence_id: int,
                  activity: dict) -> None:
        await self.execute("""INSERT INTO api.c2s_user_statuses
                                          (username, status_id, sequence_id, activity)
                              VALUES ($1, $2, $3, $4)
                              ON CONFLICT (username, status_id) DO NOTHING""",
                           username,
                           status_id,
                           sequence_id,
                           activity)

    async def update_status(self, username: str, status_id: str, activity: dict) -> None:
        await self.execute("""UPDATE api.c2s_user_statuses
                              SET activity = $3
                              WHERE username = $1 AND status_id = $2""",
                           username,
                           status_id,
                           activity)

    async def count(self, username: str) -> int:
        row = await self.fetch_one("""SELECT COUNT(*) AS n
                                      FROM api.c2s_user_statuses
                                      WHERE username = $1""",
                                   username)
        return row["n"] if row else 0

    async def delete_status(self, username: str, status_id: str) -> None:
        await self.execute("""DELETE FROM api.c2s_user_statuses
                              WHERE username = $1 AND status_id = $2""",
                           username,
                           status_id)

    async def fetch(self, username: str, limit: int = 20) -> List[tuple[int, dict]]:
        rows = await self.fetch_all("""SELECT sequence_id, activity
                                       FROM api.c2s_user_statuses
                                       WHERE username = $1
                                       ORDER BY sequence_id DESC
                                       LIMIT $2""",
                                    username,
                                    limit)
        return [(row["sequence_id"], row["activity"]) for row in rows]


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("User statuses storage is not initialized.")
    return _instance

