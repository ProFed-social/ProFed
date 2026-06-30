# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock
from profed.components.api import c2s


def _record_initializers(monkeypatch):
    awaited = []

    def _fake_initializer(storage, projection, handle_events, name):
        async def _init(config):
            awaited.append(name)
        return _init

    monkeypatch.setattr(c2s, "_projection_initializer", _fake_initializer)
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
                        "v1_timelines",
                        "v2_search",
                        "v1_media",
                        "v2_media",
                        "oauth"])

    assert "c2s_known_accounts" not in awaited
