# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from uuid import uuid4
from profed.core.media_storage import StoredFile


class FakeMediaStorage:
    def __init__(self, base_url: str = "https://fake.example.com"):
        self._files    = {}
        self._base_url = base_url.rstrip("/")

    def url_for(self, file_id: str, variant: str | None = None) -> str:
        suffix = f"_{variant}" if variant else ""
        return f"{self._base_url}/{file_id}{suffix}"

    async def store(self, data, content_type):
        file_id = str(uuid4()).replace("-", "")
        self._files[file_id] = (data, content_type)

        return StoredFile(file_id=file_id,
                          url=self.url_for(file_id),
                          content_type=content_type,
                          size=len(data))

    async def add_variant(self, file_id, variant, data, content_type):
        self._files[f"{file_id}_{variant}"] = (data, content_type)

        return StoredFile(file_id=file_id, url=self.url_for(file_id, variant),
                          content_type=content_type, size=len(data))

    async def retrieve(self, file_id: str) -> bytes:
        return self._files[file_id][0]

    async def delete(self, file_id: str) -> None:
        del self._files[file_id]

