# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from profed.components.follow_handler import handler


FOLLOW_ID = "https://mastodon.social/alice#follows/1"
FOLLOW_REST = {"actor": "https://mastodon.social/users/alice",
               "object": "https://example.com/actors/cdonat"}


def _enqueue(fake_bus,
             event_type: str = "Follow",
             object_id: str = FOLLOW_ID,
             activity_rest: dict = None,
             username: str = "cdonat"):
    fake_bus.topic("incoming_activities").messages = [(1,
                                                       event_type,
                                                       object_id,
                                                       datetime.now(timezone.utc),
                                                       {"username": username,
                                                        "activity": FOLLOW_REST
                                                                    if activity_rest is None else
                                                                    activity_rest})]


@pytest.mark.asyncio
async def test_follow_publishes_follower_accepted(fake_bus):
    _enqueue(fake_bus)

    with patch.object(handler,
                      "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()

    published = fake_bus.topic("followers").published
    assert len(published) == 1
    assert published[0]["event_type"] == "accepted"
    assert published[0]["object_id"] == "alice@mastodon.social|cdonat@example.com"
    assert published[0]["payload"] == {}


@pytest.mark.asyncio
async def test_follow_publishes_accept_activity(fake_bus):
    _enqueue(fake_bus)

    with patch.object(handler, "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()

    published = fake_bus.topic("raw_activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Accept"
    assert published[0]["payload"]["username"] == "cdonat"
    assert published[0]["payload"]["activity"]["actor"] == "https://example.com/actors/cdonat"


@pytest.mark.asyncio
async def test_follow_webfinger_failure_publishes_nothing(fake_bus):
    _enqueue(fake_bus)

    with patch.object(handler, "lookup_acct", new=AsyncMock(return_value=None)):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("followers").published   == []
    assert fake_bus.topic("raw_activities").published  == []


@pytest.mark.asyncio
async def test_invalid_follow_is_ignored(fake_bus):
    _enqueue(fake_bus,
             activity_rest={"actor": "",
                            "object": "https://example.com/actors/cdonat"})

    with patch.object(handler,
                      "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("followers").published == []


@pytest.mark.asyncio
async def test_undo_follow_publishes_follower_deleted(fake_bus):
    _enqueue(fake_bus,
             event_type="Undo",
             object_id="https://mastodon.social/alice#undos/1",
             activity_rest={"actor": "https://mastodon.social/users/alice",
                            "object": {"id": FOLLOW_ID,
                                       "type": "Follow",
                                       "actor": "https://mastodon.social/users/alice",
                                       "object": "https://example.com/actors/cdonat"}})

    with patch.object(handler,
                      "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()

    published = fake_bus.topic("followers").published
    assert len(published) == 1
    assert published[0]["event_type"] == "deleted"
    assert published[0]["object_id"] == "alice@mastodon.social|cdonat@example.com"


@pytest.mark.asyncio
async def test_undo_non_follow_is_ignored(fake_bus):
    _enqueue(fake_bus,
             event_type="Undo",
             object_id="https://mastodon.social/alice#undos/1",
             activity_rest={"actor": "https://mastodon.social/users/alice",
                            "object": {"type": "Like",
                                       "actor": "https://mastodon.social/users/alice",
                                       "object": "https://example.com/actors/cdonat"}})

    with patch.object(handler,
                      "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("followers").published == []


@pytest.mark.asyncio
async def test_non_follow_activity_is_ignored(fake_bus):
    _enqueue(fake_bus,
             event_type="Like",
             activity_rest={"actor": "https://mastodon.social/users/alice",
                            "object": "https://example.com/actors/cdonat"})

    with patch.object(handler,
                      "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("followers").published == []
    assert fake_bus.topic("raw_activities").published == []

