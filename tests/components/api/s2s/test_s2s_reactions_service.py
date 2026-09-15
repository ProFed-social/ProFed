# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from profed.core.config import raw, config
from profed.components.api.s2s.outbox import reactions_service as service
from profed.components.api.s2s.outbox import reactions_storage as storage_module


NOTE = "https://example.com/actors/alice/notes/7"


class FakeStorage:
    def __init__(self, rows):
        self.rows = rows
        self.asked = []

    async def count_for(self, object_url, emoji_only=False):
        return len([row for row in self.rows if row["emoji"] or not emoji_only])

    async def page(self, object_url, limit, before=None, emoji_only=False):
        self.asked.append({"before": before, "emoji_only": emoji_only, "limit": limit})
        rows = [row for row in self.rows
                if (before is None or row["status_id"] < before) and (row["emoji"] or not emoji_only)]
        return sorted(rows, key=lambda row: -row["status_id"])[:limit]


def _row(n, emoji="🎉"):
    return {"reaction_url": f"https://r.example/users/bob#react/{n}",
            "actor_url": "https://r.example/users/bob",
            "emoji": emoji,
            "status_id": n}


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {"PROFED_EXAMPLE__DOMAIN": "example.com", "PROFED_PROFED__RUN": "api"}

    config.reset()
    yield
    raw.paths, raw.argv, os.environ = backup


@pytest.fixture
def store(cfg):
    backup = storage_module._instance

    def _use(rows):
        storage_module._instance = FakeStorage(rows)
        return storage_module._instance

    yield _use
    storage_module._instance = backup


async def _resolve(name, page=False, before=None):
    return await service.resolve_reactions("alice", "7", name, page, before)


@pytest.mark.asyncio
async def test_a_collection_counts_and_points_at_its_first_page(store):
    store([_row(1), _row(2)])

    collection = await _resolve("likes")

    assert collection["type"] == "OrderedCollection"
    assert collection["id"] == f"{NOTE}/likes"
    assert collection["totalItems"] == 2
    assert collection["first"] == f"{NOTE}/likes?page=true"
    assert "orderedItems" not in collection


@pytest.mark.asyncio
async def test_a_page_carries_the_reactions_as_likes(store):
    store([_row(1)])

    page = await _resolve("likes", page=True)

    assert page["type"] == "OrderedCollectionPage"
    assert page["partOf"] == f"{NOTE}/likes"
    assert page["orderedItems"] == [{"id": "https://r.example/users/bob#react/1",
                                     "type": "Like",
                                     "actor": "https://r.example/users/bob",
                                     "object": NOTE,
                                     "content": "🎉"}]


@pytest.mark.asyncio
async def test_a_bare_like_carries_no_content(store):
    store([_row(1, emoji="")])

    page = await _resolve("likes", page=True)

    assert "content" not in page["orderedItems"][0]


@pytest.mark.asyncio
async def test_the_newest_reaction_comes_first(store):
    store([_row(1), _row(3), _row(2)])

    page = await _resolve("likes", page=True)

    assert [item["id"].rsplit("/", 1)[1] for item in page["orderedItems"]] == ["3", "2", "1"]


@pytest.mark.asyncio
async def test_a_full_page_points_at_the_next_one(store):
    store([_row(n) for n in range(1, service.PAGE_SIZE + 5)])

    page = await _resolve("likes", page=True)

    assert page["next"] == f"{NOTE}/likes?page=true&before=5"


@pytest.mark.asyncio
async def test_the_last_page_points_nowhere(store):
    store([_row(1), _row(2)])

    assert "next" not in await _resolve("likes", page=True)


@pytest.mark.asyncio
async def test_a_before_marker_opens_a_page_without_asking(store):
    keeper = store([_row(1), _row(2), _row(3)])

    page = await _resolve("likes", before=3)

    assert page["type"] == "OrderedCollectionPage"
    assert keeper.asked[0]["before"] == 3
    assert [item["id"].rsplit("/", 1)[1] for item in page["orderedItems"]] == ["2", "1"]


@pytest.mark.asyncio
async def test_emoji_reactions_leave_the_bare_likes_out(store):
    keeper = store([_row(1), _row(2, emoji="")])

    collection = await _resolve("emojiReactions")
    page = await _resolve("emojiReactions", page=True)

    assert collection["totalItems"] == 1
    assert keeper.asked[0]["emoji_only"] is True
    assert [item["id"].rsplit("/", 1)[1] for item in page["orderedItems"]] == ["1"]


@pytest.mark.asyncio
async def test_likes_keep_the_bare_ones(store):
    keeper = store([_row(1), _row(2, emoji="")])

    collection = await _resolve("likes")
    await _resolve("likes", page=True)

    assert collection["totalItems"] == 2
    assert keeper.asked[0]["emoji_only"] is False

