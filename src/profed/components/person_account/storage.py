# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


_COLUMNS = ("followers", "following", "statuses")


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None)

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              person_account.counters (username  TEXT   PRIMARY KEY,
                                                       followers BIGINT NOT NULL DEFAULT 0,
                                                       following BIGINT NOT NULL DEFAULT 0,
                                                       statuses  BIGINT NOT NULL DEFAULT 0)""")

    async def bump(self, username: str, column: str, delta: int) -> int:
        if column not in _COLUMNS:
            raise ValueError(f"unknown counter column: {column!r}")

        row = await self.fetch_one(f"""INSERT INTO person_account.counters (username, {column})
                                       VALUES ($1, GREATEST($2, 0))
                                       ON CONFLICT (username) DO UPDATE
                                           SET {column} = GREATEST(
                                                   person_account.counters.{column} + $2, 0)
                                       RETURNING {column}""",
                                   username,
                                   delta)
        return row[column] if row else 0

    async def get(self, username: str) -> dict:
        row = await self.fetch_one("""SELECT followers, following, statuses
                                      FROM person_account.counters
                                      WHERE username = $1""",
                                   username)
        return row or {"followers": 0, "following": 0, "statuses": 0}


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("person_account storage not initialised")
    return _instance

