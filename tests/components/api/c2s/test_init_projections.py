# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock
from profed.components.api import c2s


def _record_initializers(monkeypatch):
    awaited = []

    def _fake_initializer(projection, handle_events, name):
        async def _init(config):
            awaited.append(name)
        return _init

    monkeypatch.setattr(c2s, "_projection_initializer", _fake_initializer)
    monkeypatch.setattr(c2s.statuses_compressor, "start", lambda config: None)
    monkeypatch.setattr(c2s.statuses_sweeper, "start", lambda config: None)
    monkeypatch.setattr(c2s, "init_media_storage", AsyncMock())
    monkeypatch.setattr(c2s.oauth, "init", AsyncMock())
    monkeypatch.setattr(c2s.v1, "init", AsyncMock())
    monkeypatch.setattr(c2s.v2, "init", AsyncMock())

    return awaited


async def test_timelines_only_node_initializes_known_accounts_projection(monkeypatch):
    awaited = _record_initializers(monkeypatch)
    await c2s.init({}, ["v1_search", "v1_accounts", "v2_search", "v1_media", "v2_media", "oauth"])

    assert "c2s_known_accounts" in awaited


async def test_known_accounts_projection_skipped_when_no_reader_is_active(monkeypatch):
    awaited = _record_initializers(monkeypatch)
    await c2s.init({}, ["v1_search",
                        "v1_accounts",
                        "v1_statuses",
                        "v1_pleroma",
                        "profed_reactions",
                        "v1_timelines",
                        "v2_search",
                        "v1_media",
                        "v2_media",
                        "oauth"])

    assert "c2s_known_accounts" not in awaited


async def test_the_reaction_history_alone_still_gets_its_projections(monkeypatch):
    awaited = _record_initializers(monkeypatch)
    await c2s.init({}, ["v1_search",
                        "v1_accounts",
                        "v1_statuses",
                        "v1_pleroma",
                        "v1_timelines",
                        "v2_search",
                        "v1_media",
                        "v2_media",
                        "oauth",
                        "profed_timeline"])

    assert "c2s_known_accounts" in awaited
    assert "c2s_statuses" in awaited


async def test_the_accounts_router_brings_the_follows_projection(monkeypatch):
    awaited = _record_initializers(monkeypatch)
    await c2s.init({}, ["v1_search", "v2_search", "v1_media", "v2_media", "oauth"])

    assert "c2s_follows" in awaited


async def test_without_the_accounts_router_there_is_no_follows_projection(monkeypatch):
    awaited = _record_initializers(monkeypatch)
    await c2s.init({}, ["v1_accounts", "v1_media", "v2_media", "oauth"])

    assert "c2s_follows" not in awaited


async def test_the_accounts_router_brings_the_actors_projection(monkeypatch):
    awaited = _record_initializers(monkeypatch)
    await c2s.init({}, ["v1_search", "v2_search", "v1_media", "v2_media", "oauth"])

    assert "c2s_actor" in awaited


async def test_the_initializer_hands_the_config_to_the_projection(monkeypatch):
    projection = Mock(init=AsyncMock(), rebuild=AsyncMock())
    monkeypatch.setattr(c2s.asyncio, "create_task", lambda coro, name=None: coro.close())

    await c2s._projection_initializer(projection, AsyncMock(), "probe")({"host": "db"})

    projection.init.assert_awaited_once_with({"host": "db"})


async def test_the_initializer_prepares_the_projection_before_rebuilding_it(monkeypatch):
    order = []
    projection = Mock(init=AsyncMock(side_effect=lambda c: order.append("init")),
                      rebuild=AsyncMock(side_effect=lambda: order.append("rebuild")))
    monkeypatch.setattr(c2s.asyncio, "create_task", lambda coro, name=None: coro.close())

    await c2s._projection_initializer(projection, AsyncMock(), "probe")({})

    assert order == ["init", "rebuild"]

