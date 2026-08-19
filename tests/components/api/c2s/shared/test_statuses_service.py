# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.api.c2s.shared.statuses import service


def _row(status, actor="https://x/actors/alice"):
    return {"actor_url": actor,
            "reblog_of_url": None,
            "status": status,
            "content": {"status": status, "actor": actor}}


def _patches(store):
    return (patch("profed.components.api.c2s.shared.statuses.service.cached_multiple",
                  AsyncMock(return_value={})),
            patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                  AsyncMock(return_value=store)))


@pytest.mark.asyncio
async def test_make_statuses_resolves_in_reply_to_id_to_the_parent_mastodon_id():
    row = _row({"id": "5", "in_reply_to_id": "https://x/notes/1"})
    store = AsyncMock(mastodon_ids_for=AsyncMock(return_value={"https://x/notes/1": "99"}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id == "99"
    store.mastodon_ids_for.assert_awaited_once_with(["https://x/notes/1"])


@pytest.mark.asyncio
async def test_make_statuses_leaves_in_reply_to_id_none_when_the_parent_is_unknown():
    row = _row({"id": "5", "in_reply_to_id": "https://x/unknown"})
    store = AsyncMock(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id is None


@pytest.mark.asyncio
async def test_make_statuses_skips_the_lookup_for_a_top_level_post():
    row = _row({"id": "5", "in_reply_to_id": None})
    store = AsyncMock(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id is None
    store.mastodon_ids_for.assert_not_awaited()

