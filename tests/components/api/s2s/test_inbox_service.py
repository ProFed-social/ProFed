# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.api.s2s.inbox import storage as storage_module
from profed.components.api.s2s.inbox.service import accept_inbox_activity
from profed.components.api.s2s.inbox import service


@pytest.fixture
def fake_storage():
    instance = Mock()
    instance.exists = AsyncMock(return_value=True)
    storage_module.overwrite(instance)
    yield instance
    storage_module.overwrite(None)


ACTIVITY = {"id": "https://mastodon.social/alice#follows/1",
            "type": "Follow",
            "actor": "https://mastodon.social/users/alice",
            "object": "https://example.com/actors/cdonat"}


@pytest.mark.asyncio
async def test_publishes_event_with_event_type_and_payload(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", ACTIVITY)

    published = fake_bus.topic("incoming_activities").published

    assert len(published) == 1
    assert published[0]["event_type"] == "Follow"
    assert published[0]["object_id"] == ACTIVITY["id"]
    assert published[0]["payload"]["username"] == "cdonat"
    assert published[0]["payload"]["activity"]["actor"] == ACTIVITY["actor"]
    assert "id"   not in published[0]["payload"]["activity"]
    assert "type" not in published[0]["payload"]["activity"]


@pytest.mark.asyncio
async def test_returns_false_for_unknown_user(fake_bus, fake_storage):
    fake_storage.exists.return_value = False

    result = await accept_inbox_activity("unknown", ACTIVITY)

    assert result is False
    assert fake_bus.topic("incoming_activities").published == []


CREATE_ACTIVITY = {"id": "https://mastodon.social/alice/statuses/1",
                   "type": "Create",
                   "actor": "https://mastodon.social/users/alice",
                   "object": {"type": "Note",
                              "content": "<p>hi</p><script>steal()</script>",
                              "attributedTo": "https://mastodon.social/users/alice"}}


@pytest.mark.asyncio
async def test_publishes_sanitized_activity_content(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", CREATE_ACTIVITY)

    published = fake_bus.topic("incoming_activities").published
    assert published[0]["payload"]["activity"]["object"]["content"] == "<p>hi</p>"


@pytest.mark.asyncio
async def test_preserves_actor_and_ids_through_sanitisation(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", CREATE_ACTIVITY)

    published = fake_bus.topic("incoming_activities").published
    assert published[0]["object_id"] == CREATE_ACTIVITY["id"]
    assert published[0]["payload"]["activity"]["actor"] == CREATE_ACTIVITY["actor"]


@pytest.mark.asyncio
async def test_a_known_actor_yields_its_public_key():
    store = Mock(get_by_actor_url=AsyncMock(return_value={"public_key_pem": "PEM"}))

    with patch.object(service, "public_keys_storage", AsyncMock(return_value=store)):
        assert await service._public_key_pem("https://r.example/actor") == "PEM"


@pytest.mark.asyncio
async def test_an_unknown_actor_has_no_public_key():
    store = Mock(get_by_actor_url=AsyncMock(return_value=None))

    with patch.object(service, "public_keys_storage", AsyncMock(return_value=store)):
        assert await service._public_key_pem("https://r.example/actor") is None


@pytest.mark.asyncio
async def test_requesting_an_actor_reports_its_url(fake_bus):
    await service.request_actor("https://r.example/actor")
 
    published = fake_bus.topic("unknown_actors").published
    assert [(p["event_type"], p["object_id"]) for p in published] == \
           [("discovered_url", "https://r.example/actor")]
 
 
@pytest.mark.asyncio
async def test_the_same_actor_is_requested_once_per_window(fake_bus):
    await service.request_actor("https://r.example/actor")
    await service.request_actor("https://r.example/actor")
 
    assert len(fake_bus.topic("unknown_actors").published) == 1
 
 
@pytest.mark.asyncio
async def test_two_actors_are_requested_separately(fake_bus):
    await service.request_actor("https://r.example/one")
    await service.request_actor("https://r.example/two")
 
    assert len(fake_bus.topic("unknown_actors").published) == 2
 
 
def test_the_request_id_changes_with_the_window():
    with patch.object(service, "REQUEST_WINDOW", 1):
        first = service._request_id("https://r.example/actor")
 
    with patch.object(service, "REQUEST_WINDOW", 100000):
        assert service._request_id("https://r.example/actor") != first


@pytest.mark.asyncio
async def test_accepts_type_as_array(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", {"id":     "https://r.example/act/1",
                                           "type":   ["Follow"],
                                           "actor":  "https://r.example/a",
                                           "object": "https://example.com/actors/cdonat"})

    published = fake_bus.topic("incoming_activities").published
    assert published[0]["event_type"] == "Follow"


@pytest.mark.asyncio
async def test_normalizes_actor_object(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", {"id":     "https://r.example/act/1",
                                           "type":   "Follow",
                                           "actor":  {"id": "https://r.example/a", "type": "Person"},
                                           "object": "https://example.com/actors/cdonat"})

    published = fake_bus.topic("incoming_activities").published
    assert published[0]["payload"]["activity"]["actor"] == "https://r.example/a"


@pytest.mark.asyncio
async def test_raises_for_activity_without_id(fake_bus, fake_storage):
    with pytest.raises(ValueError):
        await accept_inbox_activity("cdonat", {"type": "Follow", "actor": "https://r.example/a"})

