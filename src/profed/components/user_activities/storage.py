# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, "user_activities")

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS user_activities.state
                                  (username TEXT PRIMARY KEY,
                                   created_seq BIGINT NOT NULL,
                                   last_changed_seq BIGINT NOT NULL,
                                   deleted_seq BIGINT,
                                   profile JSONB NOT NULL)""")
        await self.execute("""CREATE TABLE IF NOT EXISTS user_activities.meta
                                  (last_tick_seq BIGINT NOT NULL)""")
        await self.execute("""INSERT INTO user_activities.meta (last_tick_seq)
                              VALUES (0)""")

    async def upsert_created(self, username: str, profile: dict, seq: int) -> None:
        await self.execute("""INSERT INTO user_activities.state
                                  (username, created_seq, last_changed_seq, deleted_seq, profile)
                              VALUES ($1, $2, $2, NULL, $3)
                              ON CONFLICT (username) DO UPDATE
                                  SET created_seq = $2,
                                      last_changed_seq = $2,
                                      deleted_seq = NULL,
                                      profile = $3""",
                           username, seq, profile)

    async def merge_change(self, username: str, partial: dict, seq: int) -> None:
        await self.execute("""UPDATE user_activities.state
                              SET profile = profile || $2,
                                  last_changed_seq = $3
                              WHERE username = $1""",
                           username, partial, seq)

    async def mark_deleted(self, username: str, seq: int) -> None:
        await self.execute("""UPDATE user_activities.state
                              SET deleted_seq = $2,
                                  last_changed_seq = $2
                              WHERE username = $1""",
                           username, seq)

    async def remove(self, username: str) -> None:
        await self.execute("""DELETE FROM user_activities.state
                              WHERE username = $1""",
                           username)

    async def pending_since(self, last_tick_seq: int) -> list[dict]:
        return await self.fetch_all("""SELECT username,
                                              created_seq,
                                              last_changed_seq,
                                              deleted_seq,
                                              profile
                                       FROM user_activities.state
                                       WHERE last_changed_seq > $1
                                       ORDER BY last_changed_seq""",
                                    last_tick_seq)

    async def last_tick_seq(self) -> int:
        row = await self.fetch_one("SELECT last_tick_seq FROM user_activities.meta")
        return row["last_tick_seq"] if row is not None else 0

    async def set_last_tick_seq(self, seq: int) -> None:
        await self.execute("UPDATE user_activities.meta SET last_tick_seq = $1", seq)


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("user_activities storage is not initialized.")
    return _instance

