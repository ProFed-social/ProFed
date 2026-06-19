# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import profed.components.api.c2s.shared.known_accounts.storage as storage_module
from profed.components.api.c2s.shared.known_accounts.service import (lookup_by_id,
                                                                     lookup_by_acct,
                                                                     lookup_by_actor_url,
                                                                     make_account,
                                                                     WEBFINGER_CACHE_TTL)
from profed.identity import account_id

 
NOW   = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
FRESH = datetime.now(timezone.utc) - timedelta(hours=1)
STALE = datetime.now(timezone.utc) - timedelta(days=30)

ACCT      = "alice@example.com"
ACTOR_URL = "https://example.com/actors/alice"
ACCOUNT_ID = 1234
ACTOR_DATA = {"type": "Person", "name": "Alice", "published": "2026-01-01T00:00:00+00:00"}
ACCOUNT = make_account({"acct": ACCT, "actor_url": ACTOR_URL, "actor_data": ACTOR_DATA})
 
STORED_ROW = {"account_id": ACCOUNT_ID,
              "acct": ACCT,
              "actor_url": ACTOR_URL,
              "account": ACCOUNT.model_dump(),
              "last_webfinger_at": FRESH}

REMOTE_ACCT = "mallory@remote.example"
REMOTE_ACTOR_URL = "https://remote.example/actors/mallory"
REMOTE_ACCOUNT = make_account({"acct": REMOTE_ACCT,
                               "actor_url": REMOTE_ACTOR_URL,
                               "actor_data": ACTOR_DATA})
REMOTE_ROW = {"account_id": ACCOUNT_ID,
              "acct": REMOTE_ACCT,
              "actor_url": REMOTE_ACTOR_URL,
              "account": REMOTE_ACCOUNT.model_dump(),
              "last_webfinger_at": FRESH} 


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = Mock()
    storage_module._instance.get_by_id       = AsyncMock()
    storage_module._instance.get_by_acct     = AsyncMock()
    storage_module._instance.get_by_actor_url = AsyncMock()
    yield storage_module._instance
    storage_module._instance = backup
 
 
@pytest.mark.asyncio
async def test_lookup_by_id_returns_fresh_row(fake_storage):
    fake_storage.get_by_id.return_value = STORED_ROW
    result = await lookup_by_id(ACCOUNT_ID)

    assert result == ACCOUNT
 
 
@pytest.mark.asyncio
async def test_lookup_by_id_returns_none_when_not_found(fake_storage):
    fake_storage.get_by_id.return_value = None
    result = await lookup_by_id(ACCOUNT_ID)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_by_id_refreshes_stale_row(fake_storage):
    stale_row = {**REMOTE_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_id.return_value = stale_row
    with patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock(return_value=REMOTE_ACCOUNT)) as mock_wf:
        result = await lookup_by_id(ACCOUNT_ID)

    mock_wf.assert_awaited_once_with(REMOTE_ACCT)
    assert result == REMOTE_ACCOUNT
 
 
@pytest.mark.asyncio
async def test_lookup_by_acct_returns_fresh_row(fake_storage):
    fake_storage.get_by_acct.return_value = STORED_ROW
    result = await lookup_by_acct(ACCT)

    assert result == ACCOUNT
 
 
@pytest.mark.asyncio
async def test_lookup_by_acct_does_webfinger_when_not_found(fake_storage):
    fake_storage.get_by_acct.return_value = None
    with patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock(return_value=ACCOUNT)) as mock_wf:
        result = await lookup_by_acct(ACCT)
    mock_wf.assert_awaited_once_with(ACCT)

    assert result == ACCOUNT
 
 
@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_fresh_row(fake_storage):
    fake_storage.get_by_actor_url.return_value = STORED_ROW
    result = await lookup_by_actor_url(ACTOR_URL)

    assert result == ACCOUNT
 
 
@pytest.mark.asyncio
async def test_lookup_by_actor_url_does_webfinger_when_stale(fake_storage):
    stale_row = {**REMOTE_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_actor_url.return_value = stale_row
    with patch("profed.components.api.c2s.shared.known_accounts.service.lookup_acct",
               AsyncMock(return_value=REMOTE_ACCT)), \
         patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock(return_value=REMOTE_ACCOUNT)) as mock_wf:
        await lookup_by_actor_url(REMOTE_ACTOR_URL)

    mock_wf.assert_awaited_once_with(REMOTE_ACCT)
 
 
@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_stale_row_when_webfinger_fails(fake_storage):
    stale_row = {**REMOTE_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_actor_url.return_value = stale_row
    with patch("profed.components.api.c2s.shared.known_accounts.service.lookup_acct",
               AsyncMock(return_value=None)):
        result = await lookup_by_actor_url(REMOTE_ACTOR_URL)

    assert result == REMOTE_ACCOUNT


@pytest.mark.asyncio
async def test_lookup_by_id_treats_local_account_as_fresh(fake_storage):
    stale_local = {**STORED_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_id.return_value = stale_local
    with patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock()) as mock_wf:
        result = await lookup_by_id(ACCOUNT_ID)

    mock_wf.assert_not_awaited()
    assert result == ACCOUNT


ROW_FULL = {"account_id": 123456,
            "acct":       "bob@remote.example",
            "actor_url":  "https://remote.example/actors/bob",
            "actor_data": {"type":                     "Person",
                           "name":                     "Bob Example",
                           "summary":                  "A test user",
                           "icon":                     {"url": "https://remote.example/avatar.png"},
                           "image":                    {"url": "https://remote.example/header.png"},
                           "manuallyApprovesFollowers": False}}


ROW_MINIMAL = {"account_id": 42,
               "acct":       "carol@other.example",
               "actor_url":  "https://other.example/actors/carol",
               "actor_data": {"type": "Person"}}


ROW_BOT = {"account_id": 99,
           "acct":       "bot@example.com",
           "actor_url":  "https://example.com/actors/bot",
           "actor_data": {"type": "Service"}}


def test_make_account_returns_correct_fields():
    result = make_account(ROW_FULL)

    assert result.id           == account_id(ROW_FULL["acct"])
    assert result.username     == "bob"
    assert result.acct         == "bob@remote.example"
    assert result.display_name == "Bob Example"
    assert result.note         == "A test user"
    assert result.url          == "https://remote.example/actors/bob"
    assert result.avatar       == "https://remote.example/avatar.png"
    assert result.header       == "https://remote.example/header.png"
    assert result.locked       is False
    assert result.bot          is False


def test_make_account_falls_back_to_username_for_display_name():
    result = make_account(ROW_MINIMAL)

    assert result.display_name == "carol"


def test_make_account_sets_bot_flag_for_service_type():
    result = make_account(ROW_BOT)

    assert result.bot is True


def test_make_account_handles_missing_actor_data():
    row    = {**ROW_MINIMAL, "actor_data": None}
    result = make_account(row)

    assert result.display_name == "carol"
    assert result.avatar       is None
    assert result.header       is None


def test_make_account_sets_created_at_when_present():
    created = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    result  = make_account({**ROW_FULL, "created_at": created})

    assert result.created_at == created.isoformat()

