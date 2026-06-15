# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock
from profed.components.api.c2s.v1.accounts.follows.storage import _Storage


def _store(rows):
    store = _Storage(None)
    store.fetch_all = AsyncMock(return_value=rows)
    return store


@pytest.mark.asyncio
async def test_relationships_maps_following_requested_followed_by():
    store = _store([{"follower": "alice@example.com",
                     "follower_id": 1,
                     "following": "bob@remote.example",
                     "following_id": 11,
                     "state": "accepted"},
                    {"follower": "alice@example.com",
                     "follower_id": 1,
                     "following": "carol@remote.example",
                     "following_id": 22,
                     "state": "requested"},
                    {"follower": "dan@remote.example",
                     "follower_id": 33,
                     "following": "alice@example.com",
                     "following_id": 1,
                     "state": "accepted"}])

    result = await store.relationships("alice@example.com", [11, 22, 33])

    assert result[11] == {"following": True, "requested": False, "followed_by": False}
    assert result[22] == {"following": False, "requested": True, "followed_by": False}
    assert result[33] == {"following": False, "requested": False, "followed_by": True}


@pytest.mark.asyncio
async def test_relationships_defaults_unknown_target_to_false():
    store = _store([])

    result = await store.relationships("alice@example.com", [99])

    assert result[99] == {"following": False, "requested": False, "followed_by": False}


@pytest.mark.asyncio
async def test_get_followers_returns_accts():
    store = _Storage(None)
    store.fetch_all = AsyncMock(return_value=[{"follower": "bob@remote.example"},
                                              {"follower": "carol@remote.example"}])

    assert await store.get_followers("alice@example.com") == ["bob@remote.example",
                                                              "carol@remote.example"]

