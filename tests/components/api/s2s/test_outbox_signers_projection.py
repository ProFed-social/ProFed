# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.s2s.outbox import signers_projection as projection
from profed.components.api.s2s.outbox import signers_storage as storage_module


FETCHED = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)

KEY = "-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"


class FakeStorage:
    def __init__(self):
        self.rows = {}

    async def upsert(self, actor_url, actor_type, public_key_pem, fetched_at):
        self.rows[actor_url] = {"actor_type": actor_type, "public_key_pem": public_key_pem, "fetched_at": fetched_at}


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()

    yield storage_module._instance

    storage_module._instance = backup


def _payload(actor_url, actor_type, key=KEY):
    return {"actor_url": actor_url,
            "actor_data": {"type": actor_type} | ({"publicKey": {"publicKeyPem": key}} if key else {}),
            "last_webfinger_at": FETCHED.isoformat()}


@pytest.mark.asyncio
async def test_a_persons_key_is_remembered(fake_storage):
    await projection._discovered("1", _payload("https://r.example/users/bob", "Person"))

    assert fake_storage.rows["https://r.example/users/bob"] == {"actor_type": "Person",
                                                                "public_key_pem": KEY,
                                                                "fetched_at": FETCHED}


@pytest.mark.asyncio
async def test_a_servers_key_is_remembered_with_its_type(fake_storage):
    await projection._discovered("2", _payload("https://r.example/actor", "Application"))

    assert fake_storage.rows["https://r.example/actor"]["actor_type"] == "Application"


@pytest.mark.asyncio
async def test_an_actor_without_a_key_is_not_remembered(fake_storage):
    await projection._discovered("3", _payload("https://r.example/users/carol", "Person", key=None))

    assert fake_storage.rows == {}


@pytest.mark.asyncio
async def test_a_snapshot_item_is_remembered_like_an_event(fake_storage):
    await projection._discovered_snapshot(_payload("https://r.example/actor", "Service"))

    assert fake_storage.rows["https://r.example/actor"]["actor_type"] == "Service"

