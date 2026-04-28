# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import profed.components.api.c2s.shared.known_accounts.storage as storage_module
from profed.components.api.c2s.shared.known_accounts.service import (
    lookup_by_id,
    lookup_by_acct,
    lookup_by_actor_url,
    WEBFINGER_CACHE_TTL)
 
 
NOW   = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
FRESH = datetime.now(timezone.utc) - timedelta(hours=1)
STALE = datetime.now(timezone.utc) - timedelta(days=30)

ACCT      = "alice@example.com"
ACTOR_URL = "https://example.com/actors/alice"
ACCOUNT_ID = 1234
 
STORED_ROW = {"account_id":        ACCOUNT_ID,
              "acct":              ACCT,
              "actor_url":         ACTOR_URL,
              "actor_data":        {"type": "Person", "name": "Alice"},
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

    assert result == STORED_ROW
 
 
@pytest.mark.asyncio
async def test_lookup_by_id_returns_none_when_not_found(fake_storage):
    fake_storage.get_by_id.return_value = None
    result = await lookup_by_id(ACCOUNT_ID)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_by_id_refreshes_stale_row(fake_storage):
    stale_row = {**STORED_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_id.return_value = stale_row
    with patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock(return_value={**STORED_ROW, "last_webfinger_at": NOW})) as mock_wf:
        result = await lookup_by_id(ACCOUNT_ID)
    mock_wf.assert_awaited_once_with(ACCT)

    assert result["last_webfinger_at"] == NOW
 
 
@pytest.mark.asyncio
async def test_lookup_by_acct_returns_fresh_row(fake_storage):
    fake_storage.get_by_acct.return_value = STORED_ROW
    result = await lookup_by_acct(ACCT)

    assert result == STORED_ROW
 
 
@pytest.mark.asyncio
async def test_lookup_by_acct_does_webfinger_when_not_found(fake_storage):
    fake_storage.get_by_acct.return_value = None
    with patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock(return_value=STORED_ROW)) as mock_wf:
        result = await lookup_by_acct(ACCT)
    mock_wf.assert_awaited_once_with(ACCT)

    assert result == STORED_ROW
 
 
@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_fresh_row(fake_storage):
    fake_storage.get_by_actor_url.return_value = STORED_ROW
    result = await lookup_by_actor_url(ACTOR_URL)

    assert result == STORED_ROW
 
 
@pytest.mark.asyncio
async def test_lookup_by_actor_url_does_webfinger_when_stale(fake_storage):
    stale_row = {**STORED_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_actor_url.return_value = stale_row
    with patch("profed.components.api.c2s.shared.known_accounts.service.lookup_acct",
               AsyncMock(return_value=ACCT)), \
         patch("profed.components.api.c2s.shared.known_accounts.service._do_webfinger_lookup",
               AsyncMock(return_value=STORED_ROW)) as mock_wf:
        result = await lookup_by_actor_url(ACTOR_URL)

    mock_wf.assert_awaited_once_with(ACCT)
 
 
@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_stale_row_when_webfinger_fails(fake_storage):
    stale_row = {**STORED_ROW, "last_webfinger_at": STALE}
    fake_storage.get_by_actor_url.return_value = stale_row
    with patch("profed.components.api.c2s.shared.known_accounts.service.lookup_acct",
               AsyncMock(return_value=None)):
        result = await lookup_by_actor_url(ACTOR_URL)

    assert result == stale_row

