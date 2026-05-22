# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.core import message_bus
from profed.components.api.s2s.inbox import storage as storage_module
from profed.components.api.s2s.inbox.service import accept_inbox_activity


@pytest.fixture
def fake_storage():
    instance = Mock()
    instance.exists = AsyncMock(return_value=True)
    storage_module.overwrite(instance)
    yield instance
    storage_module.overwrite(None)


ACTIVITY = {"type":  "Follow",
            "actor": "https://mastodon.social/users/alice",
            "object": "https://example.com/actors/cdonat"}


@pytest.mark.asyncio
async def test_publishes_event_with_type_and_payload(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", ACTIVITY)
    
    published = fake_bus.topic("incoming_activities").published
    
    assert len(published) == 1
    assert published[0]["type"] == "incoming"
    assert published[0]["payload"]["username"] == "cdonat"
    assert published[0]["payload"]["activity"] == ACTIVITY


@pytest.mark.asyncio
async def test_returns_false_for_unknown_user(fake_bus, fake_storage):
    fake_storage.exists.return_value = False
    
    result = await accept_inbox_activity("unknown", ACTIVITY)
    
    assert result is False
    assert fake_bus.topic("incoming_activities").published == []

