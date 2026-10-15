# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              preview_activities.media (file_id TEXT PRIMARY KEY,
                                                        url TEXT NOT NULL,
                                                        content_type TEXT NOT NULL,
                                                        width INTEGER,
                                                        height INTEGER)""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              preview_activities.variant (file_id TEXT NOT NULL,
                                                          variant TEXT NOT NULL,
                                                          PRIMARY KEY (file_id, variant))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              preview_activities_media_url ON preview_activities.media (url)""")

    async def remember(self,
                       file_id: str,
                       url: str,
                       content_type: str,
                       width: Optional[int],
                       height: Optional[int]) -> None:
        await self.execute("""INSERT INTO preview_activities.media
                                    (file_id, url, content_type, width, height)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (file_id) DO UPDATE
                              SET url          = excluded.url,
                                  content_type = excluded.content_type,
                                  width        = excluded.width,
                                  height       = excluded.height""",
                           file_id,
                           url,
                           content_type,
                           width,
                           height)

    async def forget(self, file_id: str) -> None:
        await self.execute("""DELETE FROM
                                  preview_activities.variant
                              WHERE
                                  file_id = $1""",
                           file_id)
        await self.execute("""DELETE FROM
                                  preview_activities.media
                              WHERE
                                  file_id = $1""",
                           file_id)

    async def note_variant(self, file_id: str, variant: str) -> None:
        await self.execute("""INSERT INTO preview_activities.variant
                                    (file_id, variant)
                              VALUES ($1, $2)
                              ON CONFLICT (file_id, variant) DO NOTHING""",
                           file_id,
                           variant)

    async def known(self, urls: List[str]) -> List[dict]:
        return await self.fetch_all("""SELECT
                                           m.file_id,
                                           m.url,
                                           m.content_type,
                                           m.width,
                                           m.height,
                                           COALESCE(array_agg(v.variant)
                                                        FILTER (WHERE v.variant IS NOT NULL),
                                                    '{}') AS variants
                                       FROM
                                           preview_activities.media AS m LEFT JOIN
                                           preview_activities.variant AS v ON v.file_id = m.file_id
                                       WHERE
                                           m.url = ANY($1::text[])
                                       GROUP BY
                                           m.file_id,
                                           m.url,
                                           m.content_type,
                                           m.width,
                                           m.height""",
                                    urls)


_instance = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("preview_activities storage not initialized")
    return _instance

