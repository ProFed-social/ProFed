# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              polish_activities.actors
                                    (acct      TEXT PRIMARY KEY,
                                     actor_url TEXT NOT NULL)""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              polish_activities.unfinished_objects
                                    (url        TEXT        PRIMARY KEY,
                                     event_type TEXT        NOT NULL,
                                     object_id  TEXT        NOT NULL,
                                     payload    JSONB       NOT NULL,
                                     emitted_at TIMESTAMPTZ NOT NULL)""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              polish_activities.unresolved_actors
                                    (acct TEXT NOT NULL,
                                     url  TEXT NOT NULL REFERENCES polish_activities.unfinished_objects (url)
                                          ON DELETE CASCADE,
                                     PRIMARY KEY (acct, url))""")

    async def remember_actor(self, acct: str, actor_url: str) -> None:
        await self.execute("""INSERT INTO polish_activities.actors
                                    (acct, actor_url)
                              VALUES ($1, $2)
                              ON CONFLICT (acct) DO UPDATE
                                  SET actor_url = EXCLUDED.actor_url""",
                           acct,
                           actor_url)

    async def forget_actor(self, acct: str) -> None:
        await self.execute("""DELETE FROM polish_activities.actors
                              WHERE acct = $1""",
                           acct)

    async def url_for(self, acct: str) -> Optional[str]:
        row = await self.fetch_one("""SELECT actor_url
                                      FROM polish_activities.actors
                                      WHERE acct = $1""",
                                   acct)
        return row["actor_url"] if row is not None else None

    async def hold(self, url, event_type, object_id, payload, emitted_at, accts) -> None:
        await self.execute("""INSERT INTO polish_activities.unfinished_objects
                                    (url, event_type, object_id, payload, emitted_at)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (url) DO UPDATE
                                  SET event_type = EXCLUDED.event_type,
                                      object_id  = EXCLUDED.object_id,
                                      payload    = EXCLUDED.payload,
                                      emitted_at = EXCLUDED.emitted_at""",
                           url,
                           event_type,
                           object_id,
                           payload,
                           emitted_at)
        await self.execute("""DELETE FROM polish_activities.unresolved_actors
                              WHERE url = $1
                                AND acct <> ALL ($2::text[])""",
                           url,
                           accts)
        await self.execute("""INSERT INTO polish_activities.unresolved_actors
                                    (acct, url)
                              SELECT acct, $1
                              FROM unnest($2::text[]) AS acct
                              ON CONFLICT (acct, url) DO NOTHING""",
                           url,
                           accts)

    async def release(self, url: str) -> None:
        await self.execute("""DELETE FROM polish_activities.unfinished_objects
                              WHERE url = $1""",
                           url)

    async def waiting_for(self, acct: str) -> List[dict]:
        return await self.fetch_all("""SELECT o.url, o.event_type, o.object_id, o.payload, o.emitted_at
                                       FROM polish_activities.unfinished_objects AS o
                                       JOIN polish_activities.unresolved_actors AS u
                                         ON u.url = o.url
                                       WHERE u.acct = $1
                                       ORDER BY o.url""",
                                    acct)

    async def drop_older_than(self, cutoff) -> None:
        await self.execute("""DELETE FROM polish_activities.unfinished_objects
                              WHERE emitted_at < $1""",
                           cutoff)


_instance: _Storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("Polish activities storage is not initialized.")
    return _instance

