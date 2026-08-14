# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from profed.components.api.c2s.profed.timeline import service


class _Status:
    def __init__(self, id):
        self.id = id


@pytest.mark.asyncio
async def test_build_block_normal_post_has_no_booster_and_no_highlights(monkeypatch):
    part_rows = [{"url": "a1", "mastodon_id": 1}, {"url": "a2", "mastodon_id": 2}]
    ao = SimpleNamespace(thread_of=AsyncMock(return_value=part_rows), boosted_parts=AsyncMock())
    monkeypatch.setattr(service.as_objects, "storage", AsyncMock(return_value=ao))
    monkeypatch.setattr(service, "make_statuses", AsyncMock(return_value=[_Status("1"), _Status("2")]))

    block = await service._build_block({"root": "a1", "booster": None, "mastodon_id": 5})

    ao.thread_of.assert_awaited_once_with("a1")
    ao.boosted_parts.assert_not_awaited()
    assert [s.id for s in block["parts"]] == ["1", "2"]
    assert block["booster"] is None
    assert block["boosted"] == set()
    assert block["cursor"] == 5


@pytest.mark.asyncio
async def test_build_block_boost_highlights_boosted_parts_and_sets_booster(monkeypatch):
    part_rows = [{"url": "a1", "mastodon_id": 1}, {"url": "a2", "mastodon_id": 2}, {"url": "a4", "mastodon_id": 4}]
    ao = SimpleNamespace(thread_of=AsyncMock(return_value=part_rows),
                         boosted_parts=AsyncMock(return_value=["a2", "a4"]))
    monkeypatch.setattr(service.as_objects, "storage", AsyncMock(return_value=ao))
    monkeypatch.setattr(service, "make_statuses",
                        AsyncMock(return_value=[_Status("1"), _Status("2"), _Status("4")]))
    monkeypatch.setattr(service, "cached_multiple", AsyncMock(return_value={"X": "acct-X"}))

    block = await service._build_block({"root": "a1", "booster": "X", "mastodon_id": 6})

    ao.boosted_parts.assert_awaited_once_with("X", ["a1", "a2", "a4"])
    assert block["boosted"] == {"2", "4"}
    assert block["booster"] == "acct-X"
    assert block["cursor"] == 6


@pytest.mark.asyncio
async def test_timeline_wires_thread_roots_through_grouping(monkeypatch):
    async def rows(username):
        for row in [{"mastodon_id": 2, "root": "a1", "booster": None},
                    {"mastodon_id": 1, "root": "a1", "booster": None}]:
            yield row

    ut = SimpleNamespace(thread_roots=lambda username: rows(username))
    monkeypatch.setattr(service.user_timeline, "storage", AsyncMock(return_value=ut))
    monkeypatch.setattr(service, "_build_block", AsyncMock(side_effect=lambda row: {"cursor": row["mastodon_id"]}))

    blocks = await service.timeline("me", after=None, limit=20)

    assert [block["cursor"] async for block in blocks] == [2]

@pytest.mark.asyncio
async def test_build_block_returns_none_when_the_thread_cannot_be_resolved(monkeypatch):
    ao = SimpleNamespace(thread_of=AsyncMock(return_value=[]), boosted_parts=AsyncMock())
    monkeypatch.setattr(service.as_objects, "storage", AsyncMock(return_value=ao))
    make = AsyncMock()
    monkeypatch.setattr(service, "make_statuses", make)

    assert await service._build_block({"root": None, "booster": None, "mastodon_id": 5}) is None
    ao.thread_of.assert_awaited_once_with(None)
    make.assert_not_awaited()

