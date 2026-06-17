# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.shared.actors import storage
from profed.components.api.c2s.shared.actors.service import (resolve_actor,
                                                             resolve_actor_by_id,
                                                             resolve_actor_by_url,
                                                             with_source)
from profed.models.mastodon import Account


ACCOUNT_ROW = {"id": "1",
               "username": "alice",
               "acct": "alice@example.com",
               "display_name": "Alice Example",
               "note": "Software engineer",
               "url": "https://example.com/actors/alice"} 


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = Mock()
    storage._instance.fetch = AsyncMock()
    storage._instance.fetch_by_id = AsyncMock()
    storage._instance.fetch_by_url = AsyncMock()

    yield storage._instance

    storage._instance = backup
 
 
@pytest.mark.asyncio
async def test_resolve_actor_found(fake_storage):
    fake_storage.fetch.return_value = ACCOUNT_ROW

    account = await resolve_actor("alice")

    assert account is not None
    assert account.username == "alice"
    assert account.display_name == "Alice Example" 

 
@pytest.mark.asyncio
async def test_resolve_actor_not_found(fake_storage):
    fake_storage.fetch.return_value = None

    account = await resolve_actor("unknown")

    assert account is None


@pytest.mark.asyncio
async def test_resolve_actor_by_id_found(fake_storage):
    fake_storage.fetch_by_id.return_value = ACCOUNT_ROW
    account = await resolve_actor_by_id("1")
    assert account is not None
    assert account.id == "1"


@pytest.mark.asyncio
async def test_resolve_actor_by_id_not_found(fake_storage):
    fake_storage.fetch_by_id.return_value = None
    account = await resolve_actor_by_id("999")
    assert account is None


@pytest.mark.asyncio
async def test_resolve_actor_by_url_found(fake_storage):
    fake_storage.fetch_by_url.return_value = ACCOUNT_ROW
    account = await resolve_actor_by_url("https://example.com/actors/alice")
    assert account is not None
    assert account.url == "https://example.com/actors/alice"


@pytest.mark.asyncio
async def test_resolve_actor_by_url_not_found(fake_storage):
    fake_storage.fetch_by_url.return_value = None
    account = await resolve_actor_by_url("https://example.com/actors/ghost")
    assert account is None


def test_with_source_adds_editable_source():
    result = with_source(Account.model_validate(ACCOUNT_ROW))

    assert result.username == "alice"
    assert result.source["privacy"] == "public"
    assert result.source["note"] == "Software engineer"


def test_with_source_handles_empty_note():
    result = with_source(Account.model_validate({**ACCOUNT_ROW, "note": ""}))

    assert result.source["note"] == ""

