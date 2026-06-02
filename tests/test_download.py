# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import importlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from profed.core.media_storage import StoredFile

download_module = importlib.import_module("profed.media.download")
should_redownload = download_module.should_redownload
download = download_module.download


IMAGE_BYTES = b"\xff\xd8\xff\xe0test"
IMAGE_HASH = hashlib.sha256(IMAGE_BYTES).hexdigest()


def _fake_http_client(headers=None, content=b"", status_code=200):
    response = MagicMock()
    response.headers = headers or {}
    response.content = content
    if status_code >= 400:
        response.raise_for_status = MagicMock(side_effect=Exception(f"HTTP {status_code}"))
    else:
        response.raise_for_status = MagicMock()

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.head = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)

    return client


@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_no_cache_info():
    assert await should_redownload("https://example.com/img.jpg", None, None) is True


@pytest.mark.asyncio
async def test_should_redownload_returns_false_when_last_modified_unchanged():
    lm = "Thu, 01 Jan 2026 00:00:00 GMT"
    client = _fake_http_client(headers={"last-modified": lm})

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await should_redownload("https://example.com/img.jpg", lm, None)

    assert result is False


@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_last_modified_is_newer():
    client = _fake_http_client(headers={"last-modified": "Fri, 02 Jan 2026 00:00:00 GMT"})

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await should_redownload("https://example.com/img.jpg",
                                         "Thu, 01 Jan 2026 00:00:00 GMT",
                                         None)

    assert result is True


@pytest.mark.asyncio
async def test_should_redownload_falls_back_to_etag_when_no_last_modified_in_response():
    client = _fake_http_client(headers={"etag": '"abc123"'})

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await should_redownload("https://example.com/img.jpg",
                                         "Thu, 01 Jan 2026 00:00:00 GMT",
                                         '"abc123"')

    assert result is False


@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_etag_differs():
    client = _fake_http_client(headers={"etag": '"new-etag"'})

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await should_redownload("https://example.com/img.jpg",
                                         None,
                                         '"old-etag"')

    assert result is True


@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_head_request_fails():
    client = MagicMock()
    client.__aenter__ = AsyncMock(side_effect=Exception("timeout"))
    client.__aexit__ = AsyncMock(return_value=False)

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await should_redownload("https://example.com/img.jpg",
                                         "Thu, 01 Jan 2026 00:00:00 GMT",
                                         None)

    assert result is True


@pytest.mark.asyncio
async def test_download_returns_existing_url_when_hash_unchanged(fake_bus):
    client = _fake_http_client(content=IMAGE_BYTES,
                               headers={"content-type": "image/jpeg"})
    existing = {"url": "https://cdn.example.com/old", "content_hash": IMAGE_HASH}

    with patch.object(download_module.httpx, "AsyncClient", return_value=client), \
         patch.object(download_module, "media_storage"):
        result = await download("https://example.com/img.jpg", existing, "alice@example.com")

    assert result == ("https://cdn.example.com/old", None)


@pytest.mark.asyncio
async def test_download_stores_new_file_when_hash_differs(fake_bus):
    client = _fake_http_client(content=b"new content",
                               headers={"content-type": "image/jpeg"})
    existing = {"url": "https://cdn.example.com/old", "content_hash": IMAGE_HASH}
    stored = StoredFile(file_id="new",
                        url="https://cdn.example.com/new",
                        content_type="image/jpeg",
                        size=11)
    fake_storage = MagicMock()
    fake_storage.store = AsyncMock(return_value=stored)

    with patch.object(download_module.httpx, "AsyncClient", return_value=client), \
         patch.object(download_module, "media_storage", return_value=fake_storage):
        result = await download("https://example.com/img.jpg", existing, "alice@example.com")

    assert result == ("https://cdn.example.com/new", "new")
    published = fake_bus.topic("media").published
    assert len(published) == 1
    assert published[0]["payload"]["source_url"] == "https://example.com/img.jpg"


@pytest.mark.asyncio
async def test_download_returns_existing_url_on_http_error(fake_bus):
    client = _fake_http_client(status_code=404)
    existing = {"url": "https://cdn.example.com/old", "content_hash": IMAGE_HASH}

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await download("https://example.com/img.jpg", existing, "alice@example.com")

    assert result == ("https://cdn.example.com/old", None)


@pytest.mark.asyncio
async def test_download_returns_none_when_no_existing_and_download_fails(fake_bus):
    client = _fake_http_client(status_code=500)

    with patch.object(download_module.httpx, "AsyncClient", return_value=client):
        result = await download("https://example.com/img.jpg", None, "alice@example.com")

    assert result == (None, None)

