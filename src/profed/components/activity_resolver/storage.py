# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              activity_resolver.resolution
                                    (object_id       TEXT        PRIMARY KEY,
                                     state           TEXT        NOT NULL,
                                     version         TIMESTAMPTZ,
                                     cache_end       TIMESTAMPTZ,
                                     emitted_at      TIMESTAMPTZ NOT NULL,
                                     attempt         INT         NOT NULL DEFAULT 0,
                                     not_found_count INT         NOT NULL DEFAULT 0)""")

    async def record_process(self, object_id, state, emitted_at, attempt, not_found_count) -> None:
        await self.execute("""INSERT INTO activity_resolver.resolution
                                    (object_id, state, emitted_at, attempt, not_found_count)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (object_id) DO UPDATE
                              SET state           = excluded.state,
                                  emitted_at      = excluded.emitted_at,
                                  attempt         = excluded.attempt,
                                  not_found_count = excluded.not_found_count""",
                           object_id,
                           state,
                           emitted_at,
                           attempt,
                           not_found_count)

    async def record_version(self, object_id, state, version, cache_end, emitted_at, attempt, not_found_count) -> None:
        await self.execute("""INSERT INTO activity_resolver.resolution
                                    (object_id, state, version, cache_end, emitted_at, attempt, not_found_count)
                              VALUES ($1, $2, $3, $4, $5, $6, $7)
                              ON CONFLICT (object_id) DO UPDATE
                              SET state           = excluded.state,
                                  version         = excluded.version,
                                  cache_end       = excluded.cache_end,
                                  emitted_at      = excluded.emitted_at,
                                  attempt         = excluded.attempt,
                                  not_found_count = excluded.not_found_count
                              WHERE activity_resolver.resolution.version IS NULL
                                 OR excluded.version >= activity_resolver.resolution.version""",
                           object_id,
                           state,
                           version,
                           cache_end,
                           emitted_at,
                           attempt,
                           not_found_count)

    async def get(self, object_id):
        return await self.fetch_one("""SELECT object_id, state, version, cache_end, emitted_at, attempt, not_found_count
                                       FROM activity_resolver.resolution
                                       WHERE object_id = $1""",
                                    object_id)


_instance = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("activity_resolver storage not initialized")
    return _instance

