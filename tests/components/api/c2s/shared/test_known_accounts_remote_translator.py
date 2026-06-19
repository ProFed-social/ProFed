# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.api.c2s.shared.known_accounts.remote_translator as mod


def _fake_bus():
    published = []

    async def _publish(**kwargs):
        published.append(kwargs)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=_publish)
    ctx.__aexit__ = AsyncMock(return_value=False)
    topic = MagicMock()
    topic.publish = MagicMock(return_value=ctx)
    bus = MagicMock()
    bus.topic = MagicMock(return_value=topic)
    return bus, published


@pytest.mark.asyncio
async def test_discovered_converts_actor_to_account_and_publishes_updated():
    bus, published = _fake_bus()
    payload = {"acct": "bob@remote.example",
               "actor_url": "https://remote.example/users/bob",
               "actor_data": {"type": "Person", "name": "Bob",
                              "published": "2026-01-01T00:00:00+00:00"}}
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._discovered("777", payload, 3)

    assert bus.topic.call_args[0][0] == "known_accounts"
    assert len(published) == 1
    assert published[0]["event_type"] == "updated"
    assert published[0]["object_id"] == "777"
    account = published[0]["payload"]
    assert account["acct"] == "bob@remote.example"
    assert account["username"] == "bob"
    assert "actor_data" not in account

