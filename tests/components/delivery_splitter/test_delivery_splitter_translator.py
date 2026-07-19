# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from profed.components.delivery_splitter import translator
from profed.components.delivery_splitter import storage as storage_module


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self):
        self.recipients: dict[str, set[str]] = {}

    async def get_recipients(self, object_url):
        return set(self.recipients.get(object_url, set()))

    async def put_recipients(self, object_url, recipients):
        self.recipients[object_url] = set(recipients)

    async def drop_recipients(self, object_url):
        self.recipients.pop(object_url, None)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _payload():
    return {"username": "alice",
            "activity": {"actor": "https://example.com/actors/alice",
                         "object": {"id": "https://example.com/notes/1", "type": "Note"}}}


@pytest.mark.asyncio
async def test_create_queues_one_delivery_per_recipient(fake_bus, fake_storage):
    recipients = {"bob@remote.example", "carol@remote.example"}
    with patch.object(translator, "recipients_at", AsyncMock(return_value=recipients)), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._create("Create", "https://example.com/act/1", _payload(), AT)

    published = fake_bus.topic("deliveries").published
    assert len(published) == 2
    assert all(p["event_type"] == "queued" for p in published)
    assert {p["object_id"] for p in published} == {
        "https://example.com/act/1|bob@remote.example",
        "https://example.com/act/1|carol@remote.example"}
    assert all(p["payload"]["username"] == "alice" for p in published)
    assert all(p["payload"]["activity"]["id"] == "https://example.com/act/1" for p in published)
    assert all(p["payload"]["activity"]["type"] == "Create" for p in published)


@pytest.mark.asyncio
async def test_create_queries_recipients_at_activity_time(fake_bus, fake_storage):
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())) as rec, \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._create("Create", "https://example.com/act/1", _payload(), AT)

    rec.assert_awaited_once_with("alice@example.com", AT)


@pytest.mark.asyncio
async def test_create_without_recipients_publishes_nothing(fake_bus, fake_storage):
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._create("Create", "https://example.com/act/1", _payload(), AT)

    assert fake_bus.topic("deliveries").published == []


def test_follow_target_is_object_string():
    assert translator._follow_target({"object": "https://r.example/bob"}) == "https://r.example/bob"


def test_accept_target_is_object_actor():
    assert translator._accept_target({"object": {"actor": "https://r.example/bob"}}) == "https://r.example/bob"


def test_undo_target_is_object_object():
    assert translator._undo_target({"object": {"object": "https://r.example/bob"}}) == "https://r.example/bob"


def test_follow_target_of_dict_is_none():
    assert translator._follow_target({"object": {"type": "Note"}}) is None

 
@pytest.mark.asyncio
async def test_directed_recipients_uses_lookup_acct():
    with patch.object(translator, "lookup_acct", AsyncMock(return_value="bob@remote.example")):
        result = await translator._directed_recipients(translator._accept_target,
                                                       {"object": {"actor": "https://r.example/bob"}})

    assert result == {"bob@remote.example"}


@pytest.mark.asyncio
async def test_create_recipients_uses_recipients_at():
    with patch.object(translator, "recipients_at", AsyncMock(return_value={"x@remote.example"})), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        result = await translator._create_recipients("https://example.com/notes/1", {}, "alice", AT)

    assert result == {"x@remote.example"}


@pytest.mark.asyncio
async def test_directed_queues_to_resolved_target(fake_bus, fake_storage):
    with patch.object(translator, "lookup_acct", AsyncMock(return_value="bob@remote.example")):
        await translator._accept("Accept", "https://x/act/1",
                                 {"username": "alice",
                                  "activity": {"object": {"actor": "https://r.example/bob"}}}, AT)

    published = fake_bus.topic("deliveries").published
    assert len(published) == 1
    assert published[0]["object_id"] == "https://x/act/1|bob@remote.example"
    assert published[0]["payload"]["activity"]["type"] == "Accept"


@pytest.mark.asyncio
async def test_reject_queues_to_target_from_object_actor(fake_bus, fake_storage):
    with patch.object(translator, "lookup_acct", AsyncMock(return_value="bob@remote.example")):
        await translator._accept("Reject", "https://x/act/1",
                                 {"username": "alice",
                                  "activity": {"object": {"actor": "https://r.example/bob"}}}, AT)

    published = fake_bus.topic("deliveries").published
    assert len(published) == 1
    assert published[0]["object_id"] == "https://x/act/1|bob@remote.example"
    assert published[0]["payload"]["activity"]["type"] == "Reject"


def _payload_with_mention(mention_url="https://remote.example/actors/dave"):
    return {"username": "alice",
            "activity": {"actor": "https://example.com/actors/alice",
                         "object": {"id": "https://example.com/notes/1",
                                    "type": "Note",
                                    "tag": [{"type": "Mention", "href": mention_url,
                                             "name": "@dave@remote.example"}]}}}


@pytest.mark.asyncio
async def test_create_stores_recipients_under_the_object_url(fake_bus, fake_storage):
    with patch.object(translator, "recipients_at", AsyncMock(return_value={"bob@remote.example"})), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._create("Create", "https://example.com/act/1", _payload(), AT)

    assert fake_storage.recipients["https://example.com/notes/1"] == {"bob@remote.example"}


@pytest.mark.asyncio
async def test_create_includes_mentioned_accounts_as_recipients(fake_bus, fake_storage):
    with patch.object(translator, "recipients_at", AsyncMock(return_value={"bob@remote.example"})), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"), \
         patch.object(translator, "lookup_acct", AsyncMock(return_value="dave@remote.example")):
        await translator._create("Create", "https://example.com/act/1", _payload_with_mention(), AT)

    queued = {p["object_id"].split("|", 1)[1] for p in fake_bus.topic("deliveries").published}
    assert queued == {"bob@remote.example", "dave@remote.example"}


@pytest.mark.asyncio
async def test_update_unions_new_recipients_with_the_stored_ones(fake_bus, fake_storage):
    fake_storage.recipients["https://example.com/notes/1"] = {"dave@remote.example"}
    with patch.object(translator, "recipients_at", AsyncMock(return_value={"bob@remote.example"})), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._update("Update", "https://example.com/act/2", _payload(), AT)

    assert fake_storage.recipients["https://example.com/notes/1"] == {"bob@remote.example", "dave@remote.example"}


@pytest.mark.asyncio
async def test_update_delivers_to_recipients_who_only_saw_the_create(fake_bus, fake_storage):
    fake_storage.recipients["https://example.com/notes/1"] = {"dave@remote.example"}
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._update("Update", "https://example.com/act/2", _payload(), AT)

    queued = {p["object_id"].split("|", 1)[1] for p in fake_bus.topic("deliveries").published}
    assert "dave@remote.example" in queued


@pytest.mark.asyncio
async def test_delete_delivers_to_everyone_who_ever_received_the_object(fake_bus, fake_storage):
    fake_storage.recipients["https://example.com/notes/1"] = {"bob@remote.example", "dave@remote.example"}
    delete_payload = {"username": "alice",
                      "activity": {"actor": "https://example.com/actors/alice",
                                   "object": "https://example.com/notes/1"}}
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._delete("Delete", "https://example.com/act/3", delete_payload, AT)

    queued = {p["object_id"].split("|", 1)[1] for p in fake_bus.topic("deliveries").published}
    assert queued == {"bob@remote.example", "dave@remote.example"}


@pytest.mark.asyncio
async def test_delete_drops_the_recipients_row(fake_bus, fake_storage):
    fake_storage.recipients["https://example.com/notes/1"] = {"bob@remote.example"}
    delete_payload = {"username": "alice",
                      "activity": {"actor": "https://example.com/actors/alice",
                                   "object": "https://example.com/notes/1"}}
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._delete("Delete", "https://example.com/act/3", delete_payload, AT)

    assert "https://example.com/notes/1" not in fake_storage.recipients

