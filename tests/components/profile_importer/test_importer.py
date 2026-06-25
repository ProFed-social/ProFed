# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import httpx

from profed.components.profile_importer import importer
from profed.models.user_profile import UserProfile
from profed.models import MediaReference


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _msg(seq, event_type, object_id, payload):
    return (seq, event_type, object_id, TS, payload)


def _users(fake_bus):
    return fake_bus.topic("users")


def _mf2(name=None, summary=None):
    return {"items": [{"type": ["h-card"],
                       "properties": {key: [value]
                                      for key, value in {"name": name,
                                                         "summary": summary}.items()
                                      if value is not None}}]}


@pytest.mark.asyncio
async def test_new_profile_publishes_created(fake_bus):
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")

    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["event_type"] == "created"
    assert published[0]["object_id"] == "alice"
    assert published[0]["payload"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_changed_name_publishes_profile_edited(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    with patch.object(importer,
                      "fetch_mf2",
                      new=AsyncMock(return_value=_mf2("Alice Renamed"))):
        await importer.run_import("alice", "https://example.com/alice")

    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["event_type"] == "profile_edited"
    assert published[0]["payload"] == {"name": "Alice Renamed"}


@pytest.mark.asyncio
async def test_changed_summary_publishes_profile_edited(fake_bus):
    _users(fake_bus).messages = [_msg(1,
                                      "created",
                                      "alice",
                                      {"name": "Alice", "summary": "Old"})]

    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice", "New"))):
        await importer.run_import("alice", "https://example.com/alice")

    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["event_type"] == "profile_edited"
    assert published[0]["payload"]["summary"] == "New"
    assert "name" not in published[0]["payload"]


@pytest.mark.asyncio
async def test_unchanged_profile_publishes_nothing(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"})]
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_fetch_error_publishes_nothing(fake_bus):
    with patch.object(importer,
                      "fetch_mf2",
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
async def test_profile_importer_calls_run_import_with_default_templates(fake_bus):
    from profed.components import profile_importer as component
    with patch.object(component, "run_import", new=AsyncMock()) as mock_run:
        await component.ProfileImporter({"username": "alice", "url": "https://example.com/alice"})
        mock_run.assert_awaited_once_with("alice", "https://example.com/alice",
                                          component.DEFAULT_NAME, component.DEFAULT_SUMMARY)


@pytest.mark.asyncio
async def test_profile_importer_passes_config_templates(fake_bus):
    from profed.components import profile_importer as component
    with patch.object(component, "run_import", new=AsyncMock()) as mock_run:
        await component.ProfileImporter({"username": "alice",
                                         "url":      "https://example.com/alice",
                                         "name":     "{given-name}",
                                         "summary":  "{x-summary}"})
        mock_run.assert_awaited_once_with("alice", "https://example.com/alice",
                                          "{given-name}", "{x-summary}")


@pytest.mark.asyncio
async def test_profile_importer_defaults_username_template(fake_bus):
    from profed.components import profile_importer as component
    with patch.object(component, "run_import", new=AsyncMock()) as mock_run:
        await component.ProfileImporter({"url": "https://example.com/alice"})
        mock_run.assert_awaited_once_with(component.DEFAULT_USERNAME, "https://example.com/alice",
                                          component.DEFAULT_NAME, component.DEFAULT_SUMMARY)


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
async def test_update_does_not_emit_keys_generated(fake_bus):
    _users(fake_bus).messages = [_msg(1,
                                      "created",
                                      "alice",
                                      {"name": "Alice",
                                       "public_key_pem": "pubkey",
                                       "private_key_pem": "privkey"})]

    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice Renamed"))):
        await importer.run_import("alice", "https://example.com/alice")

    published = _users(fake_bus).published
    assert all(p["event_type"] != "keys_generated" for p in published)
    assert all(p["event_type"] != "created" for p in published)


@pytest.mark.asyncio
async def test_unchanged_profile_with_keys_publishes_nothing(fake_bus):
    _users(fake_bus).messages = [_msg(1,
                                      "created",
                                      "alice",
                                      {"name": "Alice",
                                       "public_key_pem": "pubkey",
                                       "private_key_pem": "privkey"})]
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_sync_images_downloads_when_new(monkeypatch):
    monkeypatch.setattr(importer, "should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "download", AsyncMock(return_value=("https://cdn.example.com/new", "abc")))
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice")

    result, tasks = await importer._sync_images("alice@example.com",
                                                profile,
                                                {"avatar": "https://example.com/photo.jpg"},
                                                {})
    if tasks:
        await asyncio.gather(*tasks)

    assert result.avatar == MediaReference(media_id="abc", variants={"large", "small"})


@pytest.mark.asyncio
async def test_sync_images_reuses_reference_when_not_stale(monkeypatch):
    monkeypatch.setattr(importer, "should_redownload", AsyncMock(return_value=False))
    download_mock = AsyncMock()
    monkeypatch.setattr(importer, "download", download_mock)
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice")
    media_state = {"https://example.com/photo.jpg": {"file_id": "existing-id"}}

    result, tasks = await importer._sync_images("alice@example.com",
                                                profile,
                                                {"avatar": "https://example.com/photo.jpg"},
                                                media_state)

    download_mock.assert_not_called()
    assert result.avatar == MediaReference(media_id="existing-id", variants={"large", "small"})
    assert tasks == []


@pytest.mark.asyncio
async def test_sync_images_skips_when_no_source_url(monkeypatch):
    redownload_mock = AsyncMock()
    monkeypatch.setattr(importer, "should_redownload", redownload_mock)
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice")

    result, tasks = await importer._sync_images("alice@example.com", profile, {}, {})

    assert tasks == []
    redownload_mock.assert_not_called()
    assert result.avatar is None
    assert result.header is None


@pytest.mark.asyncio
async def test_fetch_remote_profile_returns_profile_on_success(monkeypatch):
    monkeypatch.setattr(importer, "fetch_mf2", AsyncMock(return_value=_mf2("Alice")))

    result = await importer._fetch_remote_profile("https://example.com/alice/", "alice")

    assert result is not None
    profile, sources = result
    assert profile.username == "alice"


@pytest.mark.asyncio
async def test_fetch_remote_profile_returns_none_on_fetch_error(monkeypatch):
    monkeypatch.setattr(importer, "fetch_mf2", AsyncMock(side_effect=Exception("connection refused")))

    result = await importer._fetch_remote_profile("https://example.com/alice/", "alice")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_remote_profile_returns_none_when_no_hresume(monkeypatch):
    monkeypatch.setattr(importer, "fetch_mf2", AsyncMock(return_value={"items": []}))

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
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=(profile, {})))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=None))
    monkeypatch.setattr(importer, "_get_media_state", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "_sync_images", AsyncMock(return_value=(profile, [])))

    await importer.run_import("alice", "https://example.com/alice/")

    published = fake_bus.topic("users").published
    assert len(published) == 1
    assert published[0]["event_type"] == "created"


@pytest.mark.asyncio
async def test_run_import_publishes_profile_edited_when_profile_changed(fake_bus, monkeypatch):
    old = UserProfile(username="alice", name="Alice Old")
    updated = UserProfile(username="alice", name="Alice New")
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=(updated, {})))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=old))
    monkeypatch.setattr(importer, "_get_media_state", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "_sync_images", AsyncMock(return_value=(updated, [])))

    await importer.run_import("alice", "https://example.com/alice/")

    assert fake_bus.topic("users").published[0]["event_type"] == "profile_edited"


@pytest.mark.asyncio
async def test_run_import_publishes_nothing_when_profile_unchanged(fake_bus, monkeypatch):
    profile = UserProfile(username="alice", name="Alice")
    monkeypatch.setattr(importer, "_fetch_remote_profile", AsyncMock(return_value=(profile, {})))
    monkeypatch.setattr(importer, "_get_current_state", AsyncMock(return_value=profile))
    monkeypatch.setattr(importer, "_get_media_state", AsyncMock(return_value={}))
    monkeypatch.setattr(importer, "_sync_images", AsyncMock(return_value=(profile, [])))

    await importer.run_import("alice", "https://example.com/alice/")

    assert fake_bus.topic("users").published == []


@pytest.mark.asyncio
async def test_sync_images_spawns_avatar_variants_when_new_download(monkeypatch):
    monkeypatch.setattr(importer, "should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "download", AsyncMock(return_value=("https://cdn.example.com/new", "fid")))
    scale_mock = AsyncMock()
    monkeypatch.setattr(importer, "scale_image", scale_mock)
    profile = UserProfile(username="alice")

    _, tasks = await importer._sync_images("alice@example.com",
                                           profile,
                                           {"avatar": "https://example.com/photo.jpg"},
                                           {})
    await asyncio.gather(*tasks)

    assert len(tasks) == 2
    scale_mock.assert_any_call("fid", "large", width=400, height=400)
    scale_mock.assert_any_call("fid", "small", width=80,  height=80)


@pytest.mark.asyncio
async def test_sync_images_spawns_header_variant_when_new_download(monkeypatch):
    monkeypatch.setattr(importer, "should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "download",
                        AsyncMock(return_value=("https://cdn.example.com/new", "hid")))
    scale_mock = AsyncMock()
    monkeypatch.setattr(importer, "scale_image", scale_mock)
    profile = UserProfile(username="alice")

    _, tasks = await importer._sync_images("alice@example.com",
                                           profile,
                                           {"header": "https://example.com/banner.jpg"},
                                           {})
    await asyncio.gather(*tasks)

    assert len(tasks) == 1
    scale_mock.assert_called_once_with("hid", "wide", width=1500)


@pytest.mark.asyncio
async def test_sync_images_no_variants_when_hash_unchanged(monkeypatch):
    monkeypatch.setattr(importer, "should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "download",
                        AsyncMock(return_value=("https://cdn.example.com/old", None)))
    scale_mock = AsyncMock()
    monkeypatch.setattr(importer, "scale_image", scale_mock)
    profile = UserProfile(username="alice")

    _, tasks = await importer._sync_images("alice@example.com",
                                           profile,
                                           {"avatar": "https://example.com/photo.jpg"},
                                           {})

    assert tasks == []
    scale_mock.assert_not_called()


@pytest.mark.asyncio
async def test_sync_images_declares_all_variants_initially(monkeypatch):
    monkeypatch.setattr(importer, "should_redownload", AsyncMock(return_value=True))
    monkeypatch.setattr(importer, "download",
                        AsyncMock(return_value=("https://cdn.example.com/new", "fid")))
    monkeypatch.setattr(importer, "scale_image", AsyncMock())
    profile = UserProfile(username="alice")

    result, tasks = await importer._sync_images("alice@example.com",
                                                profile,
                                                {"avatar": "https://example.com/photo.jpg"},
                                                {})
    await asyncio.gather(*tasks)

    assert result.avatar.media_id == "fid"
    assert result.avatar.variants == {"large", "small"}

