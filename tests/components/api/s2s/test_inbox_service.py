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


def test_signer_is_none_without_key():
    with patch.object(service.instance_actor_projection, "signing_key", return_value=None):
        assert service._signer() is None


def test_signer_builds_make_sign_from_key():
    with patch.object(service.instance_actor_projection, "signing_key", return_value=("kid", "pem")), \
         patch.object(service, "make_sign") as make_sign:
        service._signer()

    make_sign.assert_called_once_with("kid", "pem")


@pytest.mark.asyncio
async def test_public_key_fetch_signs_federation_call():
    sign = object()
    store = Mock(get_by_actor_url=AsyncMock(return_value=None))

    with patch.object(service, "_signer", return_value=sign), \
         patch.object(service, "public_keys_storage", AsyncMock(return_value=store)), \
         patch.object(service, "fetch_and_register_actor", AsyncMock(return_value=None)) as far:
        await service._get_public_key_pem("https://r.example/actor")

    far.assert_awaited_once_with("https://r.example/actor", sign)



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

