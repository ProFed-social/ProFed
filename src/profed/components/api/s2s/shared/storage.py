# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Dict, Tuple, Any, Awaitable
from profed.core.persistence.base_storage import BaseStorage, init_pool


def build_storage(table_name: str) \
        -> Tuple[Callable[[Dict[str, str]], Awaitable[None]],
                 Callable[[], Awaitable[Any]],
                 Callable[[Any], None],
                 Callable[[Any], None]]:

    class _storage(BaseStorage):
        def __init__(self, pool):
            super().__init__(pool, None)
            self._table_name = table_name

        async def ensure_schema(self) -> None:
            await super().ensure_schema()
            await self.execute(f"""CREATE TABLE IF NOT EXISTS
                               api.{self._table_name} (username TEXT PRIMARY KEY)""")

        async def exists(self, username: str) -> bool:
            row = await self.fetch_one(f"""SELECT count(*) c
                                           FROM api.{self._table_name}
                                           WHERE username = $1""",
                                       username)
            return row["c"] > 0

        async def add(self, username: str) -> None:
            await self.execute(f"""INSERT INTO
                                   api.{self._table_name} (username)
                                   VALUES ($1)
                                   ON CONFLICT (username) DO NOTHING""",
                               username)

        async def delete(self, username: str) -> None:
            await self.execute(f"""DELETE FROM api.{self._table_name}
                                   WHERE username = $1""",
                               username)

    _instance: _storage | None = None

    async def init(config: Dict[str, str]) -> None:
        nonlocal _instance
        _instance = _storage(await init_pool(config))

    async def storage() -> _storage:
        nonlocal _instance
        if _instance is None:
            raise RuntimeError(f"{table_name.capitalize()} storage is not initialized.")
        return _instance

    def overwrite(s) -> None:
        nonlocal _instance
        _instance = s

    def reinit(pool) -> None:
        overwrite(_storage(pool))

    return init, storage, overwrite, reinit
