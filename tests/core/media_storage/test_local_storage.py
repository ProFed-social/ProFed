# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.core.media_storage.local import LocalFileStorage


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(base_path=str(tmp_path),
                            base_url= "https://example.com/media")


@pytest.mark.asyncio
async def test_store_writes_file_to_sharded_path(storage, tmp_path):
    await storage.store("abcdef123", b"hello", "image/png")

    assert (tmp_path / "ab" / "abcdef123").read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_store_returns_stored_file_metadata(storage):
    result = await storage.store("abcdef123", b"hello", "image/png")

    assert result.file_id      == "abcdef123"
    assert result.url          == "https://example.com/media/ab/abcdef123"
    assert result.content_type == "image/png"
    assert result.size         == 5


@pytest.mark.asyncio
async def test_retrieve_returns_stored_bytes(storage):
    await storage.store("abcdef123", b"imagedata", "image/jpeg")

    assert await storage.retrieve("abcdef123") == b"imagedata"


@pytest.mark.asyncio
async def test_retrieve_raises_for_unknown_file(storage):
    with pytest.raises(FileNotFoundError):
        await storage.retrieve("nonexistent")


@pytest.mark.asyncio
async def test_exists_returns_true_after_store(storage):
    await storage.store("abcdef123", b"x", "image/png")

    assert await storage.exists("abcdef123") is True


@pytest.mark.asyncio
async def test_exists_returns_false_for_unknown_file(storage):
    assert await storage.exists("nonexistent") is False


@pytest.mark.asyncio
async def test_delete_removes_file(storage, tmp_path):
    await storage.store("abcdef123", b"x", "image/png")
    await storage.delete("abcdef123")

    assert not (tmp_path / "ab" / "abcdef123").exists()


@pytest.mark.asyncio
async def test_delete_removes_empty_shard_directory(storage, tmp_path):
    await storage.store("abcdef123", b"x", "image/png")
    await storage.delete("abcdef123")

    assert not (tmp_path / "ab").exists()


@pytest.mark.asyncio
async def test_delete_keeps_shard_directory_when_not_empty(storage, tmp_path):
    await storage.store("abcdef123", b"x", "image/png")
    await storage.store("abXXXXX",   b"y", "image/png")
    await storage.delete("abcdef123")

    assert (tmp_path / "ab").exists()


@pytest.mark.asyncio
async def test_delete_silently_ignores_nonexistent_file(storage):
    await storage.delete("nonexistent")


def test_url_for_includes_shard_prefix(storage):
    assert storage.url_for("abcdef123") == "https://example.com/media/ab/abcdef123"


@pytest.mark.asyncio
async def test_init_creates_storage_with_config():
    from profed.core.media_storage.local import init
    storage = await init({"path": "/tmp/test", "base_url": "https://cdn.example.com"})

    assert storage.url_for("abcdef") == "https://cdn.example.com/ab/abcdef"

