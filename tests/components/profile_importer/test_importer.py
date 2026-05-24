# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import hashlib
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
 
import httpx
 
from profed.core import message_bus
from profed.components.profile_importer import importer
from profed.core.media_storage import StoredFile
from profed.models.user_profile import UserProfile

 
IMAGE_BYTES = b"\xff\xd8\xff\xe0test"
IMAGE_HASH  = hashlib.sha256(IMAGE_BYTES).hexdigest()
 
 
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
    client.__aexit__  = AsyncMock(return_value=False)
    client.head       = AsyncMock(return_value=response)
    client.get        = AsyncMock(return_value=response)

    return client

 
def _users(fake_bus):
    return fake_bus.topic("users")
 
 
def _mf2(name):
    return {"items": [{"type": ["h-card"],
                       "properties": {"name": [name]}}]}


@pytest.mark.asyncio
async def test_new_profile_publishes_created(fake_bus):
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
 
    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["type"] == "created"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_changed_profile_publishes_updated(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}})]
    with patch.object(importer, "fetch_mf2",
                      new=AsyncMock(return_value=_mf2("Alice Renamed"))):
        await importer.run_import("alice", "https://example.com/alice")
 
    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["type"] == "updated"
    assert published[0]["payload"]["name"] == "Alice Renamed"


@pytest.mark.asyncio
async def test_unchanged_profile_publishes_nothing(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}}) ]
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_fetch_error_publishes_nothing(fake_bus):
    with patch.object(importer, "fetch_mf2",
                      new=AsyncMock(side_effect=httpx.HTTPStatusError("404", request=None, response=None))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []
 
 
@pytest.mark.asyncio
async def test_no_mf2_content_publishes_nothing(fake_bus):
    empty_mf2 = {"items": []}
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=empty_mf2)):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_profile_importer_component_calls_run_import(fake_bus):
    from profed.components import profile_importer as component
    with patch.object(component, "run_import", new=AsyncMock()) as mock_run:
        await component.ProfileImporter({"username": "alice",
                                         "url": "https://example.com/alice"})
        mock_run.assert_awaited_once_with("alice", "https://example.com/alice")
 
 
@pytest.mark.asyncio
async def test_profile_importer_raises_without_username(fake_bus):
    from profed.components import profile_importer as component
    with pytest.raises(ValueError, match="username"):
        await component.ProfileImporter({"url": "https://example.com/alice"})
 
 
@pytest.mark.asyncio
async def test_profile_importer_raises_without_url(fake_bus):
    from profed.components import profile_importer as component
    with pytest.raises(ValueError, match="url"):
        await component.ProfileImporter({"username": "alice"})

 
@pytest.mark.asyncio
async def test_created_event_includes_key_pair(fake_bus):
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
    payload = _users(fake_bus).published[0]["payload"]
    assert "public_key_pem" in payload
    assert "private_key_pem" in payload
    assert payload["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
 
 
@pytest.mark.asyncio
async def test_updated_event_preserves_key_pair(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                       "payload": {"username": "alice",
                                                   "name": "Alice",
                                                   "public_key_pem":  "pubkey",
                                                   "private_key_pem": "privkey"}})]
    with patch.object(importer, "fetch_mf2",
                      new=AsyncMock(return_value=_mf2("Alice Renamed"))):
        await importer.run_import("alice", "https://example.com/alice")
    payload = _users(fake_bus).published[0]["payload"]
    assert payload["public_key_pem"]  == "pubkey"
    assert payload["private_key_pem"] == "privkey"
 
 
@pytest.mark.asyncio
async def test_unchanged_profile_with_keys_publishes_nothing(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                       "payload": {"username": "alice",
                                                   "name": "Alice",
                                                   "public_key_pem":  "pubkey",
                                                   "private_key_pem": "privkey"}})]
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_no_cache_info():
    assert await importer._should_redownload("https://example.com/img.jpg",
                                              None,
                                              None) is True
 
 
@pytest.mark.asyncio
async def test_should_redownload_returns_false_when_last_modified_unchanged():
    lm     = "Thu, 01 Jan 2026 00:00:00 GMT"
    client = _fake_http_client(headers={"last-modified": lm})

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._should_redownload("https://example.com/img.jpg", lm, None)
 
    assert result is False
 
 
@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_last_modified_is_newer():
    client = _fake_http_client(headers={"last-modified": "Fri, 02 Jan 2026 00:00:00 GMT"})

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._should_redownload("https://example.com/img.jpg",
                                                    "Thu, 01 Jan 2026 00:00:00 GMT",
                                                    None)
 
    assert result is True
 
 
@pytest.mark.asyncio
async def test_should_redownload_falls_back_to_etag_when_no_last_modified_in_response():
    client = _fake_http_client(headers={"etag": '"abc123"'})

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._should_redownload("https://example.com/img.jpg",
                                                    "Thu, 01 Jan 2026 00:00:00 GMT",
                                                    '"abc123"')
 
    assert result is False
 
 
@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_etag_differs():
    client = _fake_http_client(headers={"etag": '"new-etag"'})

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._should_redownload("https://example.com/img.jpg",
                                                    None,
                                                    '"old-etag"')
 
    assert result is True
 
 
@pytest.mark.asyncio
async def test_should_redownload_returns_true_when_head_request_fails():
    client = MagicMock()
    client.__aenter__ = AsyncMock(side_effect=Exception("timeout"))
    client.__aexit__  = AsyncMock(return_value=False)

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._should_redownload("https://example.com/img.jpg",
                                                    "Thu, 01 Jan 2026 00:00:00 GMT",
                                                    None)
 
    assert result is True
 
 
@pytest.mark.asyncio
async def test_download_and_store_returns_existing_url_when_hash_unchanged(fake_bus):
    client   = _fake_http_client(content=IMAGE_BYTES,
                                  headers={"content-type": "image/jpeg"})
    existing = {"url": "https://cdn.example.com/old", "content_hash": IMAGE_HASH}

    with patch.object(importer.httpx, "AsyncClient", return_value=client), \
         patch.object(importer, "media_storage"):
        result = await importer._download_and_store("https://example.com/img.jpg",
                                                     existing,
                                                     "alice@example.com")
 
    assert result == ("https://cdn.example.com/old", None)
 
 
@pytest.mark.asyncio
async def test_download_and_store_stores_new_file_when_hash_differs(fake_bus):
    client   = _fake_http_client(content=b"new content",
                                 headers={"content-type": "image/jpeg"})
    existing = {"url": "https://cdn.example.com/old", "content_hash": IMAGE_HASH}
    stored   = StoredFile(file_id="new",
                          url="https://cdn.example.com/new",
                          content_type="image/jpeg",
                          size=11)
    fake_storage = MagicMock()
    fake_storage.store = AsyncMock(return_value=stored)

    with patch.object(importer.httpx, "AsyncClient", return_value=client), \
         patch.object(importer, "media_storage", return_value=fake_storage):
        result = await importer._download_and_store("https://example.com/img.jpg",
                                                     existing,
                                                     "alice@example.com")
 
    assert result[0] == "https://cdn.example.com/new"
    published = fake_bus.topic("media").published
    assert len(published) == 1
    assert published[0]["payload"]["source_url"] == "https://example.com/img.jpg"
 
 
@pytest.mark.asyncio
async def test_download_and_store_returns_existing_url_on_http_error(fake_bus):
    client   = _fake_http_client(status_code=404)
    existing = {"url": "https://cdn.example.com/old", "content_hash": IMAGE_HASH}

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._download_and_store("https://example.com/img.jpg",
                                                     existing,
                                                     "alice@example.com")
 
    assert result == ("https://cdn.example.com/old", None)
 
 
@pytest.mark.asyncio
async def test_download_and_store_returns_none_when_no_existing_and_download_fails(fake_bus):
    client = _fake_http_client(status_code=500)

    with patch.object(importer.httpx, "AsyncClient", return_value=client):
        result = await importer._download_and_store("https://example.com/img.jpg",
                                                     None,
                                                     "alice@example.com")
 
    assert result == (None, None)
 
 
@pytest.mark.asyncio
async def test_sync_images_downloads_when_should_redownload_is_true(monkeypatch):
    monkeypatch.setattr(importer, "_should_redownload",
                        AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "_download_and_store",
                        AsyncMock(return_value=("https://cdn.example.com/new", "abc")))
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice",
                          avatar_source_url="https://example.com/photo.jpg")
 
    result, tasks = await importer._sync_images("alice@example.com", profile, {})
    if tasks:
        await asyncio.gather(*tasks)
 
    assert result.avatar_url == "https://cdn.example.com/new"
 
 
@pytest.mark.asyncio
async def test_sync_images_reuses_url_when_not_stale(monkeypatch):
    monkeypatch.setattr(importer, "_should_redownload", AsyncMock(return_value=False))
    download_mock = AsyncMock()
    monkeypatch.setattr(importer, "_download_and_store", download_mock)
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile     = UserProfile(username="alice",
                              avatar_source_url="https://example.com/photo.jpg")
    media_state = {"https://example.com/photo.jpg": {"url": "https://cdn.example.com/existing"}}
 
    result, tasks = await importer._sync_images("alice@example.com", profile, media_state)
    if tasks:
        await asyncio.gather(*tasks)
  
    download_mock.assert_not_called()
    assert result.avatar_url == "https://cdn.example.com/existing"
 
 
@pytest.mark.asyncio
async def test_sync_images_skips_when_no_source_url(monkeypatch):
    redownload_mock = AsyncMock()
    monkeypatch.setattr(importer, "_should_redownload", redownload_mock)
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice")
 
    result, tasks = await importer._sync_images("alice@example.com", profile, {})
 
    assert tasks == []
    redownload_mock.assert_not_called()
    assert result.avatar_url is None
 
 
@pytest.mark.asyncio
async def test_fetch_remote_profile_returns_profile_on_success(monkeypatch):
    monkeypatch.setattr(importer, "fetch_mf2",
                        AsyncMock(return_value=_mf2("Alice")))
 
    result = await importer._fetch_remote_profile("https://example.com/alice/", "alice")
 
    assert result is not None
    assert result.username == "alice"
 
 
@pytest.mark.asyncio
async def test_fetch_remote_profile_returns_none_on_fetch_error(monkeypatch):
    monkeypatch.setattr(importer, "fetch_mf2",
                        AsyncMock(side_effect=Exception("connection refused")))
 
    result = await importer._fetch_remote_profile("https://example.com/alice/", "alice")
 
    assert result is None
 
 
@pytest.mark.asyncio
async def test_fetch_remote_profile_returns_none_when_no_hresume(monkeypatch):
    monkeypatch.setattr(importer, "fetch_mf2",
                        AsyncMock(return_value={"items": []}))
 
    result = await importer._fetch_remote_profile("https://example.com/alice/", "alice")
 
    assert result is None
 
 
@pytest.mark.asyncio
async def test_run_import_returns_early_when_profile_not_found(fake_bus, monkeypatch):
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=None))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=None))
 
    await importer.run_import("alice", "https://example.com/alice/")
 
    assert fake_bus.topic("users").published == []
 
 
@pytest.mark.asyncio
async def test_run_import_publishes_created_for_new_profile(fake_bus, monkeypatch):
    profile = UserProfile(username="alice", name="Alice")
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=profile))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=None))
    monkeypatch.setattr(importer, "_get_media_state", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "_sync_images", AsyncMock(return_value=(profile, [])))
 
    await importer.run_import("alice", "https://example.com/alice/")
 
    published = fake_bus.topic("users").published
    assert len(published) == 1
    assert published[0]["type"] == "created"
 
 
@pytest.mark.asyncio
async def test_run_import_publishes_updated_when_profile_changed(fake_bus, monkeypatch):
    old     = UserProfile(username="alice", name="Alice Old")
    updated = UserProfile(username="alice", name="Alice New")
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=updated))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=old))
    monkeypatch.setattr(importer, "_get_media_state", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "_sync_images", AsyncMock(return_value=(updated, [])))
 
    await importer.run_import("alice", "https://example.com/alice/")
 
    assert fake_bus.topic("users").published[0]["type"] == "updated"
 
 
@pytest.mark.asyncio
async def test_run_import_publishes_nothing_when_profile_unchanged(fake_bus, monkeypatch):
    profile = UserProfile(username="alice", name="Alice")
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=profile))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=profile))
    monkeypatch.setattr(importer, "_get_media_state", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "_sync_images", AsyncMock(return_value=(profile, [])))
 
    await importer.run_import("alice", "https://example.com/alice/")
 
    assert fake_bus.topic("users").published == []
 

@pytest.mark.asyncio
async def test_sync_images_spawns_avatar_variants_when_new_download(monkeypatch):
    monkeypatch.setattr(importer, "_should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "_download_and_store",
                        AsyncMock(return_value=("https://cdn.example.com/new", "fid")))
    scale_mock = AsyncMock()
    monkeypatch.setattr(importer, "scale_image", scale_mock)
    profile = UserProfile(username="alice", avatar_source_url="https://example.com/photo.jpg")

    _, tasks = await importer._sync_images("alice@example.com", profile, {})
    await asyncio.gather(*tasks)

    assert len(tasks) == 2
    scale_mock.assert_any_call("fid", "large", width=400, height=400)
    scale_mock.assert_any_call("fid", "small", width=80,  height=80)


@pytest.mark.asyncio
async def test_sync_images_spawns_header_variant_when_new_download(monkeypatch):
    monkeypatch.setattr(importer, "_should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "_download_and_store",
                        AsyncMock(return_value=("https://cdn.example.com/new", "hid")))
    scale_mock = AsyncMock()
    monkeypatch.setattr(importer, "scale_image", scale_mock)
    profile = UserProfile(username="alice", header_source_url="https://example.com/banner.jpg")

    _, tasks = await importer._sync_images("alice@example.com", profile, {})
    await asyncio.gather(*tasks)

    assert len(tasks) == 1
    scale_mock.assert_called_once_with("hid", "wide", width=1500)


@pytest.mark.asyncio
async def test_sync_images_no_variants_when_hash_unchanged(monkeypatch):
    monkeypatch.setattr(importer, "_should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "_download_and_store",
                        AsyncMock(return_value=("https://cdn.example.com/old", None)))
    scale_mock = AsyncMock()
    monkeypatch.setattr(importer, "scale_image", scale_mock)
    profile = UserProfile(username="alice", avatar_source_url="https://example.com/photo.jpg")

    _, tasks = await importer._sync_images("alice@example.com", profile, {})

    assert tasks == []
    scale_mock.assert_not_called()


@pytest.mark.asyncio
async def test_sync_images_sets_avatar_small_url_to_same_url_initially(monkeypatch):
    monkeypatch.setattr(importer, "_should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "_download_and_store",
                        AsyncMock(return_value=("https://cdn.example.com/new", "fid")))
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice", avatar_source_url="https://example.com/photo.jpg")

    result, tasks = await importer._sync_images("alice@example.com", profile, {})
    await asyncio.gather(*tasks)

    assert result.avatar_url       == "https://cdn.example.com/new"
    assert result.avatar_small_url == "https://cdn.example.com/new"

