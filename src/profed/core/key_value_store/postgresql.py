# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging

from profed.core.config import config
from profed.core.config.database import with_database_defaults
from profed.core.persistence.base_storage import init_pool


logger = logging.getLogger(__name__)

DEFAULT_CLEANUP_INTERVAL = 3600

SCHEMA = "key_value"
TABLE = f"{SCHEMA}.entries"


class _PostgresKeyValueStore:
    def __init__(self, pool):
        self._pool = pool
        self._cleanup_task = None

    @classmethod
    async def _create(cls, pool, interval):
        self = cls(pool)
        await self._ensure_schema()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval))
        return self

    async def _ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
            await conn.execute(f"CREATE SCHEMA {SCHEMA}")
            await conn.execute(f"""CREATE TABLE {TABLE} (key        TEXT        PRIMARY KEY,
                                                         value      JSONB       NOT NULL,
                                                         expires_at TIMESTAMPTZ)""")
            await conn.execute(f"""CREATE INDEX ON {TABLE} (expires_at)
                                   WHERE expires_at IS NOT NULL""")

    async def _cleanup_loop(self, interval):
        while True:
            await asyncio.sleep(interval)
            try:
                await self.cleanup()
            except Exception:
                logger.exception("key-value store cleanup failed")

    async def get(self, key: str):
        row = await self._pool.fetchrow(f"""SELECT value
                                            FROM {TABLE}
                                            WHERE key = $1
                                              AND (expires_at IS NULL
                                                   OR expires_at > now())""",
                                        key)
        return None if row is None else row["value"]

    async def set(self, key: str, value, ttl: int | None = None) -> None:
        await self._pool.execute(f"""INSERT INTO {TABLE} (key, value, expires_at)
                                     VALUES ($1,
                                             $2,
                                             CASE WHEN $3::int IS NULL THEN NULL
                                                  ELSE now() + ($3 * interval '1 second')
                                             END)
                                     ON CONFLICT (key) DO UPDATE
                                         SET value = excluded.value,
                                             expires_at = excluded.expires_at""",
                                 key,
                                 value,
                                 ttl)

    async def delete(self, key: str) -> None:
        await self._pool.execute(f"DELETE FROM {TABLE} WHERE key = $1", key)

    async def cleanup(self) -> None:
        await self._pool.execute(f"""DELETE FROM {TABLE}
                                     WHERE expires_at IS NOT NULL
                                       AND expires_at <= now()""")


async def init(cfg):
    return await _PostgresKeyValueStore._create(await init_pool(with_database_defaults(cfg,
                                                                                       config().get("database",
                                                                                                    {}))),
                                                int(cfg.get("cleanup_interval",
                                                            DEFAULT_CLEANUP_INTERVAL)))

