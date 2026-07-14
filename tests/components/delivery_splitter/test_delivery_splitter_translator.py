# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from profed.components.delivery_splitter import translator


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)


def _payload():
    return {"username": "alice",
            "activity": {"actor": "https://example.com/actors/alice",
                         "object": {"id": "https://example.com/notes/1", "type": "Note"}}}


@pytest.mark.asyncio
async def test_fan_out_queues_one_per_recipient(fake_bus):
    recipients = {"bob@remote.example", "carol@remote.example"}
    with patch.object(translator, "recipients_at", AsyncMock(return_value=recipients)), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._fan_out("Create", "https://example.com/act/1", _payload(), AT)

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
async def test_fan_out_queries_recipients_at_activity_time(fake_bus):
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())) as rec, \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._fan_out("Create", "https://example.com/act/1", _payload(), AT)

    rec.assert_awaited_once_with("alice@example.com", AT)


@pytest.mark.asyncio
async def test_fan_out_without_recipients_publishes_nothing(fake_bus):
    with patch.object(translator, "recipients_at", AsyncMock(return_value=set())), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        await translator._fan_out("Create", "https://example.com/act/1", _payload(), AT)

    assert fake_bus.topic("deliveries").published == []


def test_target_actor_follow_is_object_string():
    assert translator._target_actor("Follow", {"object": "https://r.example/bob"}) == "https://r.example/bob"


def test_target_actor_accept_is_object_actor():
    assert translator._target_actor("Accept", {"object": {"actor": "https://r.example/bob"}}) == "https://r.example/bob"


def test_target_actor_undo_is_object_object():
    assert translator._target_actor("Undo", {"object": {"object": "https://r.example/bob"}}) == "https://r.example/bob"


def test_target_actor_broadcast_is_none():
    assert translator._target_actor("Create", {"object": {"type": "Note"}}) is None


@pytest.mark.asyncio
async def test_recipients_directed_uses_lookup_acct():
    with patch.object(translator, "lookup_acct", AsyncMock(return_value="bob@remote.example")):
        result = await translator._recipients("Accept",
                                              {"object": {"actor": "https://r.example/bob"}},
                                              "alice", AT)

    assert result == {"bob@remote.example"}


@pytest.mark.asyncio
async def test_recipients_broadcast_uses_recipients_at():
    with patch.object(translator, "recipients_at", AsyncMock(return_value={"x@remote.example"})), \
         patch.object(translator, "acct_from_username", return_value="alice@example.com"):
        result = await translator._recipients("Create", {}, "alice", AT)

    assert result == {"x@remote.example"}


@pytest.mark.asyncio
async def test_fan_out_directed_queues_to_resolved_target(fake_bus):
    with patch.object(translator, "lookup_acct", AsyncMock(return_value="bob@remote.example")):
        await translator._fan_out("Accept", "https://x/act/1",
                                  {"username": "alice",
                                   "activity": {"object": {"actor": "https://r.example/bob"}}}, AT)

    published = fake_bus.topic("deliveries").published
    assert len(published) == 1
    assert published[0]["object_id"] == "https://x/act/1|bob@remote.example"
    assert published[0]["payload"]["activity"]["type"] == "Accept"

