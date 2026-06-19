# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.known_accounts.storage as storage_module
from profed.components.api.c2s.shared.known_accounts.projection import (_discovered,
                                                                        _discovered_snapshot)


PAYLOAD = {"acct": "bob@remote.example",
           "actor_url": "https://remote.example/actors/bob",
           "actor_data": {"type": "Person",
                          "name": "Bob",
                          "published": "2026-01-01T00:00:00+00:00"},
           "last_webfinger_at": "2026-04-01T12:00:00+00:00"}


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = Mock()
    storage_module._instance.upsert = AsyncMock()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_discovered_stores_finished_account(fake_storage):
    await _discovered("123", PAYLOAD)

    fake_storage.upsert.assert_awaited_once()
    args = fake_storage.upsert.call_args[0]
    assert args[0] == 123
    account = args[3]
    assert account["acct"] == "bob@remote.example"
    assert account["username"] == "bob"
    assert account["display_name"] == "Bob"
    assert "actor_data" not in account


@pytest.mark.asyncio
async def test_discovered_snapshot_stores_finished_account(fake_storage):
    await _discovered_snapshot({**PAYLOAD, "account_id": 123})

    fake_storage.upsert.assert_awaited_once()
    account = fake_storage.upsert.call_args[0][3]
    assert account["acct"] == "bob@remote.example"
    assert "actor_data" not in account

