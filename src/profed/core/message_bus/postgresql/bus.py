# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
import asyncpg

class MessageBus:
    def __init__(self, config: Dict[str, str], pool: asyncpg.Pool):
        self._config = config
        self._pool = pool

    def topic(self, name: str):
        from .topic import Topic
        return Topic(self._pool, self._config, name)

    async def health_check(self):
        async with self._pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
