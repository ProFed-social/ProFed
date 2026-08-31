# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.remote_accounts.translator as mod


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


def test_an_actor_with_a_profile_page_uses_it():
    assert mod.profile_url({"url": "https://r.test/@bob"}, "https://r.test/users/bob") == "https://r.test/@bob"


def test_an_actor_without_a_profile_page_keeps_its_actor_url():
    assert mod.profile_url({}, "https://r.test/users/bob") == "https://r.test/users/bob"


def test_a_profile_page_that_is_no_url_is_ignored():
    assert mod.profile_url({"url": {"href": "x"}}, "https://r.test/users/bob") == "https://r.test/users/bob"


@pytest.mark.asyncio
async def test_the_account_carries_the_profile_page():
    bus, published = _fake_bus()
    payload = {"acct": "bob@r.test",
               "actor_url": "https://r.test/users/bob",
               "actor_data": {"type": "Person", "url": "https://r.test/@bob"}}

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._discovered("bob@r.test", payload, 1)

    assert published[0]["payload"]["url"] == "https://r.test/@bob"


@pytest.mark.asyncio
async def test_the_account_keeps_the_actor_url_as_uri():
    bus, published = _fake_bus()
    payload = {"acct": "bob@r.test",
               "actor_url": "https://r.test/users/bob",
               "actor_data": {"type": "Person", "url": "https://r.test/@bob"}}

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._discovered("bob@r.test", payload, 1)

    assert published[0]["payload"]["uri"] == "https://r.test/users/bob"

