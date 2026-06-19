# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.local_accounts.translator as mod


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
async def test_forward_rekeys_username_to_account_id():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus), \
         patch.object(mod, "acct_from_username", lambda u: f"{u}@example.com"), \
         patch.object(mod, "account_id", lambda a: 4242):
        await mod._forward("created", "alice", {"id": "4242", "acct": "alice@example.com"}, 7)

    assert bus.topic.call_args[0][0] == "known_accounts"
    assert len(published) == 1
    assert published[0]["event_type"] == "created"
    assert published[0]["object_id"] == "4242"
    assert published[0]["payload"]["acct"] == "alice@example.com"


@pytest.mark.asyncio
async def test_forwarder_preserves_verb_and_count_payload():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus), \
         patch.object(mod, "acct_from_username", lambda u: f"{u}@example.com"), \
         patch.object(mod, "account_id", lambda a: 1):
        await mod._forwarder("followers_changed")("alice", {"count": 3}, 1)

    assert published[0]["event_type"] == "followers_changed"
    assert published[0]["payload"] == {"count": 3}

