# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.known_accounts.storage as storage_module
from profed.components.api.c2s.shared.known_accounts.projection import (_created,
                                                                        _updated,
                                                                        _followers_changed,
                                                                        _following_changed,
                                                                        _statuses_changed,
                                                                        _deleted,
                                                                        _snapshot)


ACCOUNT = {"id": "123",
           "acct": "bob@remote.example",
           "url": "https://remote.example/actors/bob",
           "username": "bob",
           "followers_count": 0}


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = Mock()
    storage_module._instance.upsert = AsyncMock()
    storage_module._instance.update = AsyncMock()
    storage_module._instance.delete = AsyncMock()

    yield storage_module._instance

    storage_module._instance = backup


@pytest.mark.asyncio
async def test_created_stores_account(fake_storage):
    await _created("123", ACCOUNT)

    fake_storage.upsert.assert_awaited_once()
    args = fake_storage.upsert.call_args[0]
    assert args[0] == 123
    assert args[1] == "bob@remote.example"
    assert args[2] == "https://remote.example/actors/bob"
    assert args[3] == ACCOUNT


@pytest.mark.asyncio
async def test_updated_stores_account(fake_storage):
    await _updated("123", ACCOUNT)

    fake_storage.upsert.assert_awaited_once()
    assert fake_storage.upsert.call_args[0][3] == ACCOUNT


@pytest.mark.asyncio
async def test_followers_changed_merges_count(fake_storage):
    await _followers_changed("123", {"count": 5})

    fake_storage.update.assert_awaited_once_with(123, {"followers_count": 5})


@pytest.mark.asyncio
async def test_following_changed_merges_count(fake_storage):
    await _following_changed("123", {"count": 7})

    fake_storage.update.assert_awaited_once_with(123, {"following_count": 7})


@pytest.mark.asyncio
async def test_statuses_changed_merges_count(fake_storage):
    await _statuses_changed("123", {"count": 9})

    fake_storage.update.assert_awaited_once_with(123, {"statuses_count": 9})


@pytest.mark.asyncio
async def test_deleted_removes_account(fake_storage):
    await _deleted("123", {})

    fake_storage.delete.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_snapshot_stores_account(fake_storage):
    await _snapshot(ACCOUNT)

    fake_storage.upsert.assert_awaited_once()
    assert fake_storage.upsert.call_args[0][0] == 123

