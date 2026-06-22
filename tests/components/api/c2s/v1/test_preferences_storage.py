# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.api.c2s.v1.accounts.preferences.storage import _Storage, _configured_defaults
from profed.core.persistence.base_storage import BaseStorage
from profed.languages import supported


@pytest.mark.asyncio
async def test_upsert_passes_values_and_defaults():
    store = _Storage(None)
    store.execute = AsyncMock()

    await store.upsert("alice", "private", True, "de")

    assert store.execute.await_args.args[1:] == ("alice",
                                                 "private",
                                                 True,
                                                 "de",
                                                 "public",
                                                 False,
                                                 "en")


@pytest.mark.asyncio
async def test_upsert_passes_none_for_absent_fields():
    store = _Storage(None)
    store.execute = AsyncMock()

    await store.upsert("alice", None, None, None)

    assert store.execute.await_args.args[1:] == ("alice",
                                                 None,
                                                 None,
                                                 None,
                                                 "public",
                                                 False,
                                                 "en")


@pytest.mark.asyncio
async def test_get_passes_username_and_defaults():
    store = _Storage(None)
    store.fetch_one = AsyncMock(return_value=None)

    await store.get("alice")

    assert store.fetch_one.await_args.args[1:] == ("alice", "public", False, "en")


@pytest.mark.asyncio
async def test_get_returns_fetched_row():
    store = _Storage(None)
    row = {"privacy": "private", "sensitive": True, "language": "de"}
    store.fetch_one = AsyncMock(return_value=row)

    assert await store.get("alice") == row


@pytest.mark.asyncio
async def test_ensure_schema_populates_languages_from_supported():
    store = _Storage(None)
    store.execute = AsyncMock()

    with patch.object(BaseStorage, "ensure_schema", AsyncMock()):
        await store.ensure_schema()

    populate = [call
                for call in store.execute.await_args_list
                if "INSERT INTO api.languages" in call.args[0]]
    assert len(populate) == 1
    assert populate[0].args[1] == sorted(supported())


@pytest.mark.asyncio
async def test_ensure_schema_creates_privacy_enum():
    store = _Storage(None)
    store.execute = AsyncMock()

    with patch.object(BaseStorage, "ensure_schema", AsyncMock()):
        await store.ensure_schema()

    assert any("CREATE TYPE api.privacy_values" in call.args[0]
               for call in store.execute.await_args_list)


@pytest.mark.asyncio
async def test_get_credentials_passes_username_and_defaults():
    store = _Storage(None)
    store.fetch_one = AsyncMock(return_value=None)

    await store.get_credentials("alice")
    
    assert store.fetch_one.await_args.args[1:] == ("alice", "public", False, "en")


@pytest.mark.asyncio
async def test_get_credentials_returns_fetched_row():
    store = _Storage(None)
    row = {"payload": {"id": "1"},
           "follow_requests_count": 2,
           "privacy": "private",
           "sensitive": True,
           "language": "de"}
    store.fetch_one = AsyncMock(return_value=row)

    assert await store.get_credentials("alice") == row



def test_storage_uses_configured_default_instances():
    store = _Storage(None,
                     default_privacy="private",
                     default_sensitive=True,
                     default_language="ja")
    assert store.DEFAULT_PRIVACY == "private"
    assert store.DEFAULT_SENSITIVE is True
    assert store.DEFAULT_LANGUAGE == "ja"


@pytest.mark.asyncio
async def test_get_uses_configured_defaults():
    store = _Storage(None,
                     default_privacy="private",
                     default_sensitive=True,
                     default_language="ja")
    store.fetch_one = AsyncMock(return_value=None)
    await store.get("alice")
    assert store.fetch_one.await_args.args[1:] == ("alice", "private", True, "ja")


def test_configured_defaults_reads_config():
    cfg = {"preferences": {"default_privacy": "unlisted",
                           "default_sensitive": "true",
                           "default_language": "ja"}}
    with patch("profed.components.api.c2s.v1.accounts.preferences.storage.app_config",
               new=lambda: cfg):
        assert _configured_defaults() == ("unlisted", True, "ja")


def test_configured_defaults_falls_back_when_unset():
    with patch("profed.components.api.c2s.v1.accounts.preferences.storage.app_config",
               new=lambda: {}):
        assert _configured_defaults() == (None, None, None)


def test_configured_defaults_rejects_invalid_privacy_and_language():
    cfg = {"preferences": {"default_privacy": "loud",
                           "default_language": "zz-nope"}}
    with patch("profed.components.api.c2s.v1.accounts.preferences.storage.app_config",
               new=lambda: cfg):
        assert _configured_defaults() == (None, None, None)

