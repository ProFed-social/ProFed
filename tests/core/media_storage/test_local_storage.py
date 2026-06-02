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
    stored = await storage.store(b"hello", "image/png")

    assert (tmp_path / stored.file_id[:2] / stored.file_id).read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_store_generates_id_and_returns_metadata(storage):
    result = await storage.store(b"hello", "image/png")

    assert len(result.file_id)  == 32
    assert result.url           == f"https://example.com/media/{result.file_id[:2]}/{result.file_id}"
    assert result.content_type  == "image/png"
    assert result.size          == 5


@pytest.mark.asyncio
async def test_add_variant_writes_to_same_shard_with_suffix(storage, tmp_path):
    stored  = await storage.store(b"original", "image/png")
    variant = await storage.add_variant(stored.file_id, "small", b"scaled", "image/png")

    assert variant.file_id == stored.file_id
    assert variant.url     == f"https://example.com/media/{stored.file_id[:2]}/{stored.file_id}_small"
    assert (tmp_path / stored.file_id[:2] / f"{stored.file_id}_small").read_bytes() == b"scaled"


@pytest.mark.asyncio
async def test_retrieve_returns_stored_bytes(storage):
    stored = await storage.store(b"imagedata", "image/jpeg")

    assert await storage.retrieve(stored.file_id) == b"imagedata"


@pytest.mark.asyncio
async def test_retrieve_raises_for_unknown_file(storage):
    with pytest.raises(FileNotFoundError):
        await storage.retrieve("nonexistent")


@pytest.mark.asyncio
async def test_exists_returns_true_after_store(storage):
    stored = await storage.store(b"x", "image/png")

    assert await storage.exists(stored.file_id) is True


@pytest.mark.asyncio
async def test_exists_returns_false_for_unknown_file(storage):
    assert await storage.exists("nonexistent") is False


@pytest.mark.asyncio
async def test_delete_removes_file(storage, tmp_path):
    stored = await storage.store(b"x", "image/png")
    await storage.delete(stored.file_id)

    assert not (tmp_path / stored.file_id[:2] / stored.file_id).exists()


@pytest.mark.asyncio
async def test_delete_removes_empty_shard_directory(storage, tmp_path):
    stored = await storage.store(b"x", "image/png")
    await storage.delete(stored.file_id)

    assert not (tmp_path / stored.file_id[:2]).exists()


@pytest.mark.asyncio
async def test_delete_keeps_shard_directory_when_not_empty(storage, tmp_path):
    stored = await storage.store(b"x", "image/png")
    await storage.add_variant(stored.file_id, "small", b"y", "image/png")
    await storage.delete(stored.file_id)

    assert (tmp_path / stored.file_id[:2]).exists()


@pytest.mark.asyncio
async def test_delete_silently_ignores_nonexistent_file(storage):
    await storage.delete("nonexistent")


def test_url_for_includes_shard_prefix(storage):
    assert storage.url_for("abcdef123") == "https://example.com/media/ab/abcdef123"


def test_url_for_variant_appends_suffix(storage):
    assert storage.url_for("abcdef123", "small") == "https://example.com/media/ab/abcdef123_small"


@pytest.mark.asyncio
async def test_init_creates_storage_with_config():
    from profed.core.media_storage.local import init
    storage = await init({"path": "/tmp/test", "base_url": "https://cdn.example.com"})

    assert storage.url_for("abcdef") == "https://cdn.example.com/ab/abcdef"

