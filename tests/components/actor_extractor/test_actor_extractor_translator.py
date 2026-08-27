# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import patch
from profed.components.actor_extractor import translator
from profed.components.actor_extractor import storage as storage_module


class FakeStorage:
    def __init__(self):
        self.known_urls: set[str] = set()
        self.known_accts: set[str] = set()
        self.upserted: list = []
        self.deleted: list = []

    async def unknown_urls(self, urls):
        return [url for url in urls if url not in self.known_urls]

    async def unknown_accts(self, accts):
        return [acct for acct in accts if acct not in self.known_accts]

    async def upsert(self, actor_url, acct):
        self.upserted.append((actor_url, acct))

    async def delete(self, actor_url):
        self.deleted.append(actor_url)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _payload(**activity):
    return {"username": "alice", "activity": activity}


def _published(fake_bus):
    return fake_bus.topic("unknown_actors").published


@pytest.mark.asyncio
async def test_an_unknown_actor_url_is_reported(fake_bus, fake_storage):
    await translator._reporter("incoming_activities")("Create",
                                                      "https://a.test/act/1",
                                                      _payload(actor="https://a.test/actors/alice"),
                                                      7)

    assert [(p["event_type"], p["object_id"]) for p in _published(fake_bus)] == \
           [("discovered_url", "https://a.test/actors/alice")]


@pytest.mark.asyncio
async def test_a_known_actor_url_is_not_reported(fake_bus, fake_storage):
    fake_storage.known_urls.add("https://a.test/actors/alice")

    await translator._reporter("incoming_activities")("Create",
                                                      "https://a.test/act/1",
                                                      _payload(actor="https://a.test/actors/alice"),
                                                      7)

    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_an_unknown_acct_is_reported(fake_bus, fake_storage):
    activity = {"actor": "https://a.test/actors/alice",
                "object": {"tag": [{"type": "Mention",
                                    "href": "https://c.test/actors/carol",
                                    "name": "@carol@c.test"}]}}
    fake_storage.known_urls.update({"https://a.test/actors/alice", "https://c.test/actors/carol"})

    await translator._reporter("incoming_activities")("Create", "https://a.test/act/1", _payload(**activity), 7)

    assert [(p["event_type"], p["object_id"]) for p in _published(fake_bus)] == [("discovered_acct", "carol@c.test")]


@pytest.mark.asyncio
async def test_the_same_actor_named_twice_is_reported_once(fake_bus, fake_storage):
    activity = {"actor": "https://a.test/actors/alice",
                "object": {"attributedTo": "https://a.test/actors/alice"}}

    await translator._reporter("incoming_activities")("Create", "https://a.test/act/1", _payload(**activity), 7)

    assert len(_published(fake_bus)) == 1


@pytest.mark.asyncio
async def test_two_names_in_one_event_both_survive_the_deduplication(fake_bus, fake_storage):
    activity = {"actor": "https://a.test/actors/alice",
                "object": {"attributedTo": "https://b.test/actors/bob"}}

    await translator._reporter("incoming_activities")("Create", "https://a.test/act/1", _payload(**activity), 7)

    assert {p["object_id"] for p in _published(fake_bus)} == {"https://a.test/actors/alice",
                                                              "https://b.test/actors/bob"}


@pytest.mark.asyncio
async def test_reporting_the_same_event_twice_publishes_once(fake_bus, fake_storage):
    payload = _payload(actor="https://a.test/actors/alice")

    await translator._reporter("incoming_activities")("Create", "https://a.test/act/1", payload, 7)
    await translator._reporter("incoming_activities")("Create", "https://a.test/act/1", payload, 7)

    assert len(_published(fake_bus)) == 1


@pytest.mark.asyncio
async def test_the_same_name_from_two_source_topics_is_published_twice(fake_bus, fake_storage):
    payload = _payload(actor="https://a.test/actors/alice")

    await translator._reporter("incoming_activities")("Create", "https://a.test/act/1", payload, 7)
    await translator._reporter("raw_activities")("Create", "https://a.test/act/1", payload, 7)

    assert len(_published(fake_bus)) == 2


@pytest.mark.asyncio
async def test_a_discovered_remote_actor_becomes_known(fake_storage):
    await translator._remote_discovered("42", {"actor_url": "https://c.test/actors/carol",
                                               "acct": "carol@c.test"})

    assert fake_storage.upserted == [("https://c.test/actors/carol", "carol@c.test")]


@pytest.mark.asyncio
async def test_a_local_person_becomes_known(fake_storage):
    with patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._person_changed("alice", {"id": "https://example.com/actors/alice"})

    assert fake_storage.upserted == [("https://example.com/actors/alice", "alice@example.com")]


@pytest.mark.asyncio
async def test_a_deleted_person_is_forgotten(fake_storage):
    await translator._person_deleted("alice", {"id": "https://example.com/actors/alice"})

    assert fake_storage.deleted == ["https://example.com/actors/alice"]

