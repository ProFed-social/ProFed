# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.api.s2s import init


async def _started_projections(deactivate):
    started = []

    def fake_initializer(storage, projection, handle_events, name):
        async def _init(config):
            started.append(name)
        return _init

    with patch("profed.components.api.s2s._projection_initializer", side_effect=fake_initializer), \
         patch("profed.components.api.s2s.init_media_storage", AsyncMock()):
        await init({}, deactivate)
    return started


@pytest.mark.asyncio
async def test_all_projections_start_when_nothing_deactivated():
    assert await _started_projections([]) == ["s2s_webfinger", "s2s_actor", "s2s_inbox",
                                              "s2s_inbox_public_keys", "s2s_outbox",
                                              "s2s_instance_actor"]


@pytest.mark.asyncio
async def test_instance_actor_starts_when_instance_actor_router_active():
    started = await _started_projections(["webfinger", "actor", "inbox", "inbox_public_keys", "outbox"])
    assert "s2s_instance_actor" in started


@pytest.mark.asyncio
async def test_instance_actor_starts_when_inbox_active():
    started = await _started_projections(["webfinger", "actor", "inbox_public_keys", "outbox",
                                          "instance_actor"])
    assert "s2s_instance_actor" in started


@pytest.mark.asyncio
async def test_instance_actor_skipped_when_actor_and_inbox_deactivated():
    started = await _started_projections(["instance_actor", "inbox"])
    assert "s2s_instance_actor" not in started

