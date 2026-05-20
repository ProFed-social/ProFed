# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool, None, subscriber_schemas=["api_c2s_media"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.media (file_id        TEXT    PRIMARY KEY,
                                         url            TEXT    NOT NULL,
                                         preview_url    TEXT,
                                         content_type   TEXT    NOT NULL,
                                         size           INTEGER NOT NULL,
                                         uploader       TEXT    NOT NULL,
                                         width          INTEGER,
                                         height         INTEGER,
                                         preview_width  INTEGER,
                                         preview_height INTEGER,
                                         description    TEXT)""")

    async def insert(self,
                     file_id:        str,
                     url:            str,
                     preview_url:    str | None,
                     content_type:   str,
                     size:           int,
                     uploader:       str,
                     width:          int | None = None,
                     height:         int | None = None,
                     preview_width:  int | None = None,
                     preview_height: int | None = None) -> None:
        await self.execute("""INSERT INTO api.media
                                      (file_id,
                                       url,
                                       preview_url,
                                       content_type,
                                       size,
                                       uploader,
                                       width,
                                       height,
                                       preview_width,
                                       preview_height)
                              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                              ON CONFLICT (file_id) DO NOTHING""",
                           file_id,
                           url,
                           preview_url,
                           content_type,
                           size,
                           uploader,
                           width,
                           height,
                           preview_width,
                           preview_height)

    async def get_by_id(self, file_id: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT file_id, url, preview_url,
                                              content_type, size, uploader,
                                              width, height, preview_width,
                                              preview_height, description
                                         FROM api.media
                                        WHERE file_id = $1""",
                                    file_id)

    async def delete(self, file_id: str) -> None:
        await self.execute("DELETE FROM api.media WHERE file_id = $1", file_id)


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    pool      = await init_pool(config)
    _instance = _Storage(pool)


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("Media storage not initialized.")
    return _instance

