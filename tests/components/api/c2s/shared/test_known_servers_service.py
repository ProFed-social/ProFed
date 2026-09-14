# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import patch
from profed.components.api.c2s.shared.known_servers import service
from profed.components.api.c2s.shared.known_servers import storage as storage_module


LOCAL = "https://example.com/actors/alice"

REMOTE = "https://Pleroma.Test/users/bob"


class FakeStorage:
    def __init__(self, support=None):
        self.support = support
        self.asked = []

    async def support_of(self, host):
        self.asked.append(host)
        return self.support


@pytest.fixture
def fake_storage():
    backup = storage_module._instance

    def _use(support=None):
        storage_module._instance = FakeStorage(support)
        return storage_module._instance

    yield _use
    storage_module._instance = backup


def _domain():
    return patch("profed.components.api.c2s.shared.known_servers.service.is_local_actor_url",
                 new=lambda url: url.startswith("https://example.com/"))


@pytest.mark.asyncio
async def test_a_local_author_is_never_asked_about(fake_bus, fake_storage):
    store = fake_storage()

    with _domain():
        assert await service.understands_reactions(LOCAL) is True

    assert store.asked == []
    assert fake_bus.topic("known_servers").published == []


@pytest.mark.asyncio
async def test_a_supporting_host_takes_the_reaction(fake_bus, fake_storage):
    fake_storage(support=True)

    with _domain():
        assert await service.understands_reactions(REMOTE) is True

    assert fake_bus.topic("known_servers").published == []


@pytest.mark.asyncio
async def test_a_host_without_support_is_not_asked_again(fake_bus, fake_storage):
    fake_storage(support=False)

    with _domain():
        assert await service.understands_reactions(REMOTE) is False

    assert fake_bus.topic("known_servers").published == []


@pytest.mark.asyncio
async def test_an_unknown_host_is_discovered_and_falls_back(fake_bus, fake_storage):
    store = fake_storage(support=None)

    with _domain():
        assert await service.understands_reactions(REMOTE) is False

    assert store.asked == ["pleroma.test"]
    published = fake_bus.topic("known_servers").published
    assert [(message["event_type"], message["object_id"]) for message in published] == [("discovered", "pleroma.test")]


@pytest.mark.asyncio
async def test_the_same_host_is_discovered_only_once_per_window(fake_bus, fake_storage):
    fake_storage(support=None)

    with _domain():
        await service.understands_reactions(REMOTE)
        await service.understands_reactions(REMOTE)

    assert len(fake_bus.topic("known_servers").published) == 1


@pytest.mark.asyncio
async def test_an_unusable_actor_url_discovers_nothing(fake_bus, fake_storage):
    store = fake_storage(support=None)

    with _domain():
        assert await service.understands_reactions("not a url") is False

    assert store.asked == []
    assert fake_bus.topic("known_servers").published == []

