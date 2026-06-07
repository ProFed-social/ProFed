# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from pathlib import Path
from uuid import uuid4
from profed.core.media_storage import StoredFile

logger = logging.getLogger(__name__)


class LocalFileStorage:
    def __init__(self, base_path: str, base_url: str):
        self._base = Path(base_path)
        self._base_url = base_url.rstrip("/")

    def _relative_path(self, file_id: str, variant: str | None = None):
        return Path(file_id[:2]) / (f"{file_id}_{variant}" if variant else file_id)

    def _path_for(self, file_id: str, variant: str | None = None) -> Path:
        return self._base / self._relative_path(file_id, variant)

    def url_for(self, file_id: str, variant: str | None = None) -> str:
        return f"{self._base_url}/{ str(self._relative_path(file_id, variant)) }"

    async def store(self, data: bytes, content_type: str) -> StoredFile:
        return await self._write(str(uuid4()).replace("-", ""), None, data, content_type)

    async def add_variant(self,
                          file_id: str,
                          variant: str,
                          data: bytes,
                          content_type: str) -> StoredFile:
        return await self._write(file_id, variant, data, content_type)

    async def _write(self,
                     file_id: str,
                     variant: str | None,
                     data: bytes,
                     content_type: str) -> StoredFile:
        path = self._path_for(file_id, variant)

        def _do_write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_do_write)
        return StoredFile(file_id=      file_id,
                          url=          self.url_for(file_id, variant),
                          content_type= content_type,
                          size=         len(data))

    async def retrieve(self, file_id: str) -> bytes:
        path = self._path_for(file_id)

        def _read() -> bytes:
            if not path.exists():
                raise FileNotFoundError(f"Media file not found: {file_id}")
            return path.read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, file_id: str) -> None:
        path = self._path_for(file_id)

        def _delete() -> None:
            if not path.exists():
                return
            path.unlink()
            try:
                path.parent.rmdir()
            except OSError:
               pass

        await asyncio.to_thread(_delete)

    async def exists(self, file_id: str) -> bool:
        path = self._path_for(file_id)
        return await asyncio.to_thread(path.exists)


async def init(config: dict) -> LocalFileStorage:
    base_path = config.get("path", "/var/lib/profed/media")
    base_url  = config.get("base_url", "/media")
    return LocalFileStorage(base_path=base_path,
                            base_url= base_url)

