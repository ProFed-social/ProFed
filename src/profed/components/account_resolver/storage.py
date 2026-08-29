# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              account_resolver.process
                                    (source      TEXT        NOT NULL,
                                     sequence_id BIGINT      NOT NULL,
                                     entry       TEXT        NOT NULL,
                                     state       TEXT        NOT NULL,
                                     emitted_at  TIMESTAMPTZ NOT NULL,
                                     PRIMARY KEY (source, sequence_id))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              account_resolver.request
                                    (source      TEXT        NOT NULL,
                                     sequence_id BIGINT      NOT NULL,
                                     kind        TEXT        NOT NULL,
                                     ordinal     INT         NOT NULL,
                                     state       TEXT        NOT NULL,
                                     attempt     INT         NOT NULL DEFAULT 0,
                                     name        TEXT,
                                     document    JSONB,
                                     first_attempt_at TIMESTAMPTZ,
                                     emitted_at  TIMESTAMPTZ NOT NULL,
                                     PRIMARY KEY (source, sequence_id, kind, ordinal))""")

    async def record_process(self, source: str, sequence_id: int, entry: str, state: str, emitted_at) -> None:
        await self.execute("""INSERT INTO account_resolver.process
                                    (source, sequence_id, entry, state, emitted_at)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (source, sequence_id) DO UPDATE
                              SET state      = excluded.state,
                                  emitted_at = excluded.emitted_at""",
                           source,
                           sequence_id,
                           entry,
                           state,
                           emitted_at)

    async def ensure_process(self, source, sequence_id, entry, emitted_at) -> None:
        await self.execute("""INSERT INTO account_resolver.process
                                    (source, sequence_id, entry, state, emitted_at)
                              VALUES ($1, $2, $3, 'attempting', $4)
                              ON CONFLICT (source, sequence_id) DO NOTHING""",
                           source,
                           sequence_id,
                           entry,
                           emitted_at)

    async def record_request(self,
                             source,
                             sequence_id,
                             kind,
                             ordinal,
                             state,
                             attempt,
                             name,
                             document,
                             emitted_at) -> None:
        await self.execute("""INSERT INTO account_resolver.request
                                    (source, sequence_id, kind, ordinal, state, attempt, name, document,
                                     first_attempt_at, emitted_at)
                              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
                              ON CONFLICT (source, sequence_id, kind, ordinal) DO UPDATE
                              SET state            = excluded.state,
                                  attempt          = excluded.attempt,
                                  name             = excluded.name,
                                  document         = COALESCE(excluded.document, account_resolver.request.document),
                                  first_attempt_at = COALESCE(account_resolver.request.first_attempt_at,
                                                              excluded.first_attempt_at),
                                  emitted_at       = excluded.emitted_at""",
                           source,
                           sequence_id,
                           kind,
                           ordinal,
                           state,
                           attempt,
                           name,
                           document,
                           emitted_at)

    async def process(self, source: str, sequence_id: int) -> Optional[dict]:
        return await self.fetch_one("""SELECT source, sequence_id, entry, state, emitted_at
                                       FROM account_resolver.process
                                       WHERE source = $1
                                         AND sequence_id = $2""",
                                    source,
                                    sequence_id)

    async def requests(self, source: str, sequence_id: int) -> List[dict]:
        return await self.fetch_all("""SELECT kind,
                                              ordinal,
                                              state,
                                              attempt,
                                              name,
                                              document,
                                              first_attempt_at,
                                              emitted_at
                                       FROM account_resolver.request
                                       WHERE source = $1
                                         AND sequence_id = $2
                                       ORDER BY kind, ordinal""",
                                    source,
                                    sequence_id)

    async def unfinished(self) -> List[dict]:
        return await self.fetch_all("""SELECT source, sequence_id, entry, emitted_at
                                       FROM account_resolver.process
                                       WHERE state NOT IN ('resolved', 'unresolved')
                                       ORDER BY source, sequence_id""")


_instance = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("account_resolver storage not initialized")
    return _instance

