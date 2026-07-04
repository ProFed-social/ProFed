# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.federation.actors import fetch_and_register_actor


ACTOR_DATA = {"type": "Person", "publicKey": {"publicKeyPem": "X"}}


async def test_remote_actor_is_registered_on_remote_actors(fake_bus):
    with patch("profed.federation.actors.fetch_actor", AsyncMock(return_value=ACTOR_DATA)), \
         patch("profed.federation.actors.lookup_acct",
               AsyncMock(return_value="bob@remote.example")), \
         patch("profed.federation.actors.is_local", lambda acct: False):
        await fetch_and_register_actor("https://remote.example/actors/bob")

    assert len(fake_bus.topic("remote_actors").published) == 1


async def test_local_actor_is_not_registered_on_remote_actors(fake_bus):
    with patch("profed.federation.actors.fetch_actor", AsyncMock(return_value=ACTOR_DATA)), \
         patch("profed.federation.actors.lookup_acct",
               AsyncMock(return_value="alice@example.com")), \
         patch("profed.federation.actors.is_local", lambda acct: True):
        await fetch_and_register_actor("https://example.com/actors/alice")

    assert fake_bus.topic("remote_actors").published == []


PEM = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0B==\n-----END PUBLIC KEY-----\n"
REMOTE_ACTOR = {"id": "https://remote.example/users/bob",
                "type": "Person",
                "name": "Bob <b>x</b>",
                "summary": "<p>hi</p><script>steal()</script>",
                "inbox": "https://remote.example/users/bob/inbox",
                "publicKey": {"id": "https://remote.example/users/bob#main-key",
                              "owner": "https://remote.example/users/bob",
                              "publicKeyPem": PEM}}


def _patches():
    return (patch("profed.federation.actors.fetch_actor",
                  AsyncMock(return_value=dict(REMOTE_ACTOR))),
            patch("profed.federation.actors.lookup_acct",
                  AsyncMock(return_value="bob@remote.example")))


@pytest.mark.asyncio
async def test_publishes_sanitised_actor(fake_bus):
    fetch, lookup = _patches()
    with fetch, lookup:
        await fetch_and_register_actor("https://remote.example/users/bob")

    actor = fake_bus.topic("remote_actors").published[0]["payload"]["actor_data"]
    assert actor["summary"] == "<p>hi</p>"
    assert actor["name"] == "Bob x"


@pytest.mark.asyncio
async def test_preserves_public_key_pem(fake_bus):
    fetch, lookup = _patches()
    with fetch, lookup:
        await fetch_and_register_actor("https://remote.example/users/bob")

    actor = fake_bus.topic("remote_actors").published[0]["payload"]["actor_data"]
    assert actor["publicKey"]["publicKeyPem"] == PEM


@pytest.mark.asyncio
async def test_returns_sanitised_actor_with_intact_pem(fake_bus):
    fetch, lookup = _patches()
    with fetch, lookup:
        result = await fetch_and_register_actor("https://remote.example/users/bob")

    assert result["summary"] == "<p>hi</p>"
    assert result["publicKey"]["publicKeyPem"] == PEM

