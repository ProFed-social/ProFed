# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, patch
from profed.core import message_bus
from profed.components.follow_handler import handler
 
 
FOLLOW_ACTIVITY = {"id": "https://mastodon.social/alice#follows/1",
                   "type": "Follow",
                   "actor": "https://mastodon.social/users/alice",
                   "object": "https://example.com/actors/cdonat"}
 
 
@pytest.mark.asyncio
async def test_follow_publishes_follower_created(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": FOLLOW_ACTIVITY}})]
    with patch.object(handler, "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()
    published = fake_bus.topic("followers").published
    assert len(published) == 1
    assert published[0]["type"] == "created"
    assert published[0]["payload"]["follower"] == "alice@mastodon.social"
    assert published[0]["payload"]["following"] == "cdonat@example.com"
 
 
@pytest.mark.asyncio
async def test_follow_publishes_accept_activity(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": FOLLOW_ACTIVITY}})]
    with patch.object(handler, "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()
    published = fake_bus.topic("activities").published
    assert len(published) == 1
    assert published[0]["type"] == "created"
    assert published[0]["payload"]["type"] == "Accept"
    assert published[0]["payload"]["actor"] == "https://example.com/actors/cdonat"
 
 
@pytest.mark.asyncio
async def test_follow_webfinger_failure_publishes_nothing(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": FOLLOW_ACTIVITY}})]
    with patch.object(handler, "lookup_acct", new=AsyncMock(return_value=None)):
        await handler.handle_incoming_activities()
    assert fake_bus.topic("followers").published == []
    assert fake_bus.topic("activities").published == []
 
 
@pytest.mark.asyncio
async def test_invalid_follow_is_ignored(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": {"type": "Follow",
                                       "actor": "",
                                       "object": "https://example.com/actors/cdonat"}}})]
    with patch.object(handler, "lookup_acct", new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()
    assert fake_bus.topic("followers").published == []
 
 
@pytest.mark.asyncio
async def test_undo_follow_publishes_follower_deleted(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": {"id": "https://mastodon.social/alice#undos/1",
                                       "type": "Undo",
                                       "actor": "https://mastodon.social/users/alice",
                                       "object": FOLLOW_ACTIVITY}}})]
    with patch.object(handler, "lookup_acct",
                      new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()
    published = fake_bus.topic("followers").published
    assert len(published) == 1
    assert published[0]["type"] == "deleted"
    assert published[0]["payload"]["follower"] == "alice@mastodon.social"
 
 
@pytest.mark.asyncio
async def test_undo_non_follow_is_ignored(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": {"id": "https://mastodon.social/alice#undos/1",
                                       "type": "Undo",
                                       "actor": "https://mastodon.social/users/alice",
                                       "object": {"type": "Like",
                                                   "actor": "https://mastodon.social/users/alice",
                                                   "object": "https://example.com/actors/cdonat"}}}})]
    with patch.object(handler, "lookup_acct", new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()
    assert fake_bus.topic("followers").published == []


@pytest.mark.asyncio
async def test_non_follow_activity_is_ignored(fake_bus):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type": "incoming",
              "payload": {"username": "cdonat",
                          "activity": {"type": "Like",
                                       "actor": "https://mastodon.social/users/alice",
                                       "object": "https://example.com/actors/cdonat"}}})]
    with patch.object(handler, "lookup_acct", new=AsyncMock(return_value="alice@mastodon.social")):
        await handler.handle_incoming_activities()
    assert fake_bus.topic("followers").published == []
    assert fake_bus.topic("activities").published == []

