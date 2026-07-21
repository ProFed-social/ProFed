# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.polish_activities import storage as storage_module
from profed.components.polish_activities import known_accounts_projection as projection


class FakeStorage:
    def __init__(self):
        self.rows = {}

    async def ensure_schema(self):
        pass

    async def upsert(self, account_id, acct, actor_url):
        self.rows[account_id] = (acct, actor_url)

    async def delete(self, account_id):
        self.rows.pop(account_id, None)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


ACCOUNT = {"acct": "dave@remote.example", "url": "https://remote.example/actors/dave"}


@pytest.mark.asyncio
async def test_created_stores_acct_and_url(fake_storage):
    await projection._store("42", ACCOUNT)
    assert fake_storage.rows[42] == ("dave@remote.example", "https://remote.example/actors/dave")


@pytest.mark.asyncio
async def test_updated_overwrites_url(fake_storage):
    await projection._store("42", ACCOUNT)
    await projection._store("42", {"acct": "dave@remote.example",
                                   "url": "https://remote.example/actors/dave-new"})
    assert fake_storage.rows[42] == ("dave@remote.example", "https://remote.example/actors/dave-new")


@pytest.mark.asyncio
async def test_deleted_removes_account(fake_storage):
    await projection._store("42", ACCOUNT)
    await projection._deleted("42", {})
    assert 42 not in fake_storage.rows


@pytest.mark.asyncio
async def test_snapshot_stores_acct_and_url(fake_storage):
    await projection._apply_snapshot_item({"id": "7",
                                           "acct": "alice@example.com",
                                           "url": "https://example.com/actors/alice"})
    assert fake_storage.rows[7] == ("alice@example.com", "https://example.com/actors/alice")

