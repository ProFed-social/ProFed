# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.polish_activities import remote_actors
from profed.components.polish_activities import storage as storage_module


class FakeStorage:
    def __init__(self):
        self.remembered = []

    async def remember_actor(self, acct, actor_url):
        self.remembered.append((acct, actor_url))


@pytest.fixture(autouse=True)
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _payload(**overrides):
    return {"acct": "ghost@r.io", "actor_url": "https://r.io/ghost", **overrides}


@pytest.mark.asyncio
async def test_a_discovered_actor_becomes_known(store):
    with patch.object(remote_actors, "update_all_waiting", AsyncMock()):
        await remote_actors._discovered("42", _payload(), 7)

    assert store.remembered == [("ghost@r.io", "https://r.io/ghost")]


@pytest.mark.asyncio
async def test_a_discovered_actor_triggers_the_update(store):
    update_all_waiting = AsyncMock()
    with patch.object(remote_actors, "update_all_waiting", update_all_waiting):
        await remote_actors._discovered("42", _payload(), 7)

    assert update_all_waiting.await_args_list[0].args == ("ghost@r.io", 7)


@pytest.mark.asyncio
async def test_every_confirmed_alias_triggers_its_own_update(store):
    update_all_waiting = AsyncMock()
    with patch.object(remote_actors, "update_all_waiting", update_all_waiting):
        await remote_actors._discovered("42", _payload(acct_aliases=["old@r.io", "older@r.io"]), 7)

    assert [call.args[0] for call in update_all_waiting.await_args_list] == ["ghost@r.io", "old@r.io", "older@r.io"]


@pytest.mark.asyncio
async def test_without_aliases_only_the_canonical_acct_is_updated(store):
    update_all_waiting = AsyncMock()
    with patch.object(remote_actors, "update_all_waiting", update_all_waiting):
        await remote_actors._discovered("42", _payload(acct_aliases=[]), 7)

    assert update_all_waiting.await_count == 1

