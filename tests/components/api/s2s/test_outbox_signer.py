# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from profed.http.signatures import generate_key_pair, sign_request
from profed.components.api.s2s.outbox import signer
from profed.components.api.s2s.outbox import signers_storage as storage_module


BOB = "https://r.example/users/bob"

PATH = "/actors/alice/notes/7"

URL = "https://example.com" + PATH


@pytest.fixture
def keys():
    return generate_key_pair()


@pytest.fixture
def known(keys):
    backup = storage_module._instance
    public_pem, _ = keys
    storage_module._instance = Mock(signer=AsyncMock(return_value={"actor_url": BOB,
                                                                   "actor_type": "Person",
                                                                   "public_key_pem": public_pem}))

    yield storage_module._instance

    storage_module._instance = backup


@pytest.fixture
def unknown():
    backup = storage_module._instance
    storage_module._instance = Mock(signer=AsyncMock(return_value=None))

    yield storage_module._instance

    storage_module._instance = backup


def _signed(keys, key_id=BOB + "#main-key"):
    _, private_pem = keys
    return sign_request("GET", URL, b"", key_id, private_pem)


@pytest.mark.asyncio
async def test_a_request_without_a_signature_has_no_signer(fake_bus, known):
    assert await signer.signer_of("GET", PATH, {}) is None


@pytest.mark.asyncio
async def test_a_valid_signature_names_its_signer(fake_bus, known, keys):
    assert (await signer.signer_of("GET", PATH, _signed(keys)))["actor_url"] == BOB


@pytest.mark.asyncio
async def test_an_unknown_key_has_no_signer_and_is_asked_for(fake_bus, unknown, keys):
    assert await signer.signer_of("GET", PATH, _signed(keys)) is None
    assert [(p["event_type"], p["object_id"])
            for p in fake_bus.topic("unknown_actors").published] == [("discovered_url", BOB)]


@pytest.mark.asyncio
async def test_a_signature_from_another_key_has_no_signer(fake_bus, known):
    assert await signer.signer_of("GET", PATH, _signed(generate_key_pair())) is None


@pytest.mark.asyncio
async def test_a_mismatching_key_is_asked_for_again(fake_bus, known):
    await signer.signer_of("GET", PATH, _signed(generate_key_pair()))

    assert [p["object_id"] for p in fake_bus.topic("unknown_actors").published] == [BOB]


@pytest.mark.asyncio
async def test_an_old_signature_has_no_signer(fake_bus, known, keys):
    much_later = datetime.now(timezone.utc) + timedelta(hours=13)

    assert await signer.signer_of("GET", PATH, _signed(keys), now=much_later) is None


@pytest.mark.asyncio
async def test_a_signature_from_the_future_has_no_signer(fake_bus, known, keys):
    much_earlier = datetime.now(timezone.utc) - timedelta(hours=13)

    assert await signer.signer_of("GET", PATH, _signed(keys), now=much_earlier) is None


@pytest.mark.asyncio
async def test_a_signature_within_the_window_still_names_its_signer(fake_bus, known, keys):
    later = datetime.now(timezone.utc) + timedelta(hours=11)

    assert (await signer.signer_of("GET", PATH, _signed(keys), now=later))["actor_url"] == BOB


@pytest.mark.asyncio
async def test_a_signature_without_a_date_has_no_signer(fake_bus, known, keys):
    headers = {key: value for key, value in _signed(keys).items() if key != "Date"}

    assert await signer.signer_of("GET", PATH, headers) is None


@pytest.mark.asyncio
async def test_a_local_key_is_never_asked_for(fake_bus, unknown, keys):
    local = "https://example.com/actors/alice"

    assert await signer.signer_of("GET", PATH, _signed(keys, key_id=local + "#main-key")) is None
    assert fake_bus.topic("unknown_actors").published == []

