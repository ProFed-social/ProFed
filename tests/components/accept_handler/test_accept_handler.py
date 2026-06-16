# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from profed.components.accept_handler import handler
import profed.components.accept_handler.storage as storage_module


ACCEPT_ID = "https://remote.example/activities/1"
ACCEPT_REST = {"actor": "https://remote.example/actors/bob",
               "object": {"id": "https://example.com/actors/alice#follows/123456",
                          "type": "Follow",
                          "actor": "https://example.com/actors/alice",
                          "object": "https://remote.example/actors/bob"}}


def _enqueue(fake_bus,
             event_type: str = "Accept",
             object_id: str = ACCEPT_ID,
             activity_rest: dict = None,
             username:str = "alice"):
    fake_bus.topic("incoming_activities").messages = [(1,
                                                       event_type,
                                                       object_id,
                                                       datetime.now(timezone.utc),
                                                       {"username": username,
                                                        "activity": ACCEPT_REST
                                                                    if activity_rest is None else
                                                                    activity_rest})]

         
@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = Mock()
    storage_module._instance.get_by_actor_url = AsyncMock(return_value=123456)

    yield storage_module._instance

    storage_module._instance = backup


@pytest.mark.asyncio
async def test_accept_publishes_followers_accepted(fake_bus, fake_storage):
    _enqueue(fake_bus)

    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/alice"), \
         patch("profed.components.accept_handler.handler.acct_from_username",
               return_value="alice@example.com"), \
         patch("profed.components.accept_handler.handler.lookup_acct",
               AsyncMock(return_value="bob@remote.example")):
        await handler.handle_incoming_activities()

    published = fake_bus.topic("followers").published
    assert len(published) == 1
    assert published[0]["event_type"] == "accepted"
    assert published[0]["object_id"] == "alice@example.com|bob@remote.example"

 
@pytest.mark.asyncio
async def test_reject_publishes_followers_rejected(fake_bus, fake_storage):
    _enqueue(fake_bus, event_type="Reject")
 
    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/alice"), \
         patch("profed.components.accept_handler.handler.acct_from_username",
               return_value="alice@example.com"), \
         patch("profed.components.accept_handler.handler.lookup_acct",
               AsyncMock(return_value="bob@remote.example")):
        await handler.handle_incoming_activities()
 
    published = fake_bus.topic("followers").published
    assert len(published) == 1
    assert published[0]["event_type"] == "rejected"
    assert published[0]["object_id"] == "alice@example.com|bob@remote.example"
 
 
@pytest.mark.asyncio
async def test_reject_for_other_user_is_ignored(fake_bus, fake_storage):
    _enqueue(fake_bus, event_type="Reject")
 
    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/bob"):
        await handler.handle_incoming_activities()
 
    assert fake_bus.topic("followers").published == []


@pytest.mark.asyncio
async def test_accept_for_other_user_is_ignored(fake_bus, fake_storage):
    _enqueue(fake_bus)

    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/bob"):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("known_accounts").published == []


@pytest.mark.asyncio
async def test_accept_unknown_actor_is_ignored(fake_bus, fake_storage):
    storage_module._instance.get_by_actor_url = AsyncMock(return_value=None)
    _enqueue(fake_bus)

    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/alice"):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("known_accounts").published == []


@pytest.mark.asyncio
async def test_invalid_accept_is_ignored(fake_bus, fake_storage):
    _enqueue(fake_bus, activity_rest={})

    await handler.handle_incoming_activities()
    assert fake_bus.topic("known_accounts").published == []


@pytest.mark.asyncio
async def test_non_accept_activity_is_ignored(fake_bus, fake_storage):
    _enqueue(fake_bus,
             event_type="Like",
             activity_rest={"actor":  "https://remote.example/actors/bob",
                            "object": "https://example.com/notes/1"})

    await handler.handle_incoming_activities()
    assert fake_bus.topic("known_accounts").published == []

