# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.local_delivery import translator
from profed.core.message_bus.source_key import source_key


FOLLOW = {"actor": "https://example.com/actors/bob",
          "object": "https://example.com/actors/alice"}


def _incoming(fake_bus):
    return fake_bus.topic("incoming_activities").published


@pytest.mark.asyncio
async def test_a_local_delivery_reaches_the_incoming_activities(fake_bus):
    await translator._deliver("Follow", "https://example.com/follows/1", {"username": "alice", "activity": FOLLOW}, 7)

    assert [(p["event_type"], p["object_id"], p["payload"]["username"]) for p in _incoming(fake_bus)] == \
           [("Follow", "https://example.com/follows/1", "alice")]


@pytest.mark.asyncio
async def test_the_delivered_activity_carries_neither_type_nor_id(fake_bus):
    await translator._deliver("Follow", "https://example.com/follows/1", {"username": "alice", "activity": FOLLOW}, 7)

    assert _incoming(fake_bus)[0]["payload"]["activity"] == FOLLOW


@pytest.mark.asyncio
async def test_the_message_id_follows_the_sequence_of_the_delivery():
    publish = AsyncMock()

    with patch.object(translator, "publish_incoming", publish):
        await translator._deliver("Follow",
                                  "https://example.com/follows/1",
                                  {"username": "alice", "activity": FOLLOW},
                                  7)

    assert publish.await_args.args[4] == source_key("local_delivery").message_id(7)


@pytest.mark.asyncio
async def test_an_activity_with_a_malformed_actor_is_dropped(fake_bus):
    await translator._deliver("Follow",
                              "https://example.com/follows/1",
                              {"username": "alice", "activity": {"actor": 42}},
                              7)

    assert _incoming(fake_bus) == []

