# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

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

