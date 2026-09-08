# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
import os
from profed.core.config import config as profed_config, raw
from profed.components.api.c2s.shared.statuses import service


class Cfg:
    def __init__(self, cfg):
        raw.paths = []
        raw.argv = [""] + [f"--{s}.{k}={v}"
                           for s, d in cfg.items()
                           for k, v in d.items()]
        os.environ = {k: v for k, v in os.environ.items()
                      if not k.startswith("PROFED_")}

    def __enter__(self):
        profed_config.reset()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val


def _row(status, actor="https://x/actors/alice", url="https://x/notes/5"):
    return {"actor_url": actor,
            "kind": "content",
            "status": status,
            "content": {"status": status, "actor": actor, "url": url}}


def _store(**kwargs):
    return AsyncMock(**{"boost_stats": AsyncMock(return_value={}),
                        "reaction_stats": AsyncMock(return_value={}),
                        "reaction_breakdown": AsyncMock(return_value={}),
                        **kwargs})


def _patches(store):
    return (patch("profed.components.api.c2s.shared.statuses.service.cached_multiple",
                  AsyncMock(return_value={})),
            patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                  AsyncMock(return_value=store)))


@pytest.mark.asyncio
async def test_make_statuses_resolves_in_reply_to_id_to_the_parent_mastodon_id():
    row = _row({"id": "5", "in_reply_to_id": "https://x/notes/1"})
    store = _store(mastodon_ids_for=AsyncMock(return_value={"https://x/notes/1": "99"}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id == "99"
    store.mastodon_ids_for.assert_awaited_once_with(["https://x/notes/1"])


@pytest.mark.asyncio
async def test_make_statuses_leaves_in_reply_to_id_none_when_the_parent_is_unknown():
    row = _row({"id": "5", "in_reply_to_id": "https://x/unknown"})
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id is None


@pytest.mark.asyncio
async def test_make_statuses_skips_the_lookup_for_a_top_level_post():
    row = _row({"id": "5", "in_reply_to_id": None})
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id is None
    store.mastodon_ids_for.assert_not_awaited()


@pytest.mark.asyncio
async def test_make_statuses_builds_a_reply_preview_from_the_parent_content():
    row = {**_row({"id": "5"}),
           "parent_content": {"status": {"content": "<p>original</p>"},
                              "actor": "https://x/actors/bob"}}
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].reply_to is not None
    assert result[0].reply_to.content == "<p>original</p>"
    assert result[0].reply_to.account.url == "https://x/actors/bob"


@pytest.mark.asyncio
async def test_make_statuses_leaves_reply_to_none_without_parent_content():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].reply_to is None


@pytest.mark.asyncio
async def test_make_statuses_reads_the_boost_count_for_the_content_url():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   boost_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_boosts": 3,
                                                                             "reblogged": False}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].reblogs_count == 3
    store.boost_stats.assert_awaited_once_with(["https://x/notes/5"], None)


@pytest.mark.asyncio
async def test_make_statuses_marks_the_viewers_own_boost():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   boost_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_boosts": 1,
                                                                             "reblogged": True}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})], "https://x/actors/me")

    assert result[0].reblogged is True
    store.boost_stats.assert_awaited_once_with(["https://x/notes/5"], "https://x/actors/me")


@pytest.mark.asyncio
async def test_make_statuses_counts_an_unknown_content_url_as_zero():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}), boost_stats=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].reblogs_count == 0
    assert result[0].reblogged is False


@pytest.mark.asyncio
async def test_a_boost_wrapper_repeats_the_counts_of_the_boosted_status():
    row = {**_row({"id": "9"}),
           "kind": "announce",
           "status": {"id": "9"}}
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   boost_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_boosts": 2,
                                                                             "reblogged": True}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row], "https://x/actors/me")

    assert result[0].reblog.reblogs_count == 2
    assert result[0].reblogs_count == 2
    assert result[0].reblogged is True


@pytest.mark.asyncio
async def test_make_statuses_reads_the_reaction_count_for_the_content_url():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   reaction_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_reactions": 8,
                                                                                "reacted": False}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].favourites_count == 8
    assert result[0].favourited is False
    store.reaction_stats.assert_awaited_once_with(["https://x/notes/5"], None)


@pytest.mark.asyncio
async def test_make_statuses_marks_the_viewers_own_reaction():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   reaction_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_reactions": 1,
                                                                                "reacted": True}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})], "https://x/actors/me")

    assert result[0].favourited is True
    store.reaction_stats.assert_awaited_once_with(["https://x/notes/5"], "https://x/actors/me")


@pytest.mark.asyncio
async def test_a_boost_wrapper_repeats_the_reaction_counts():
    row = {**_row({"id": "9"}), "kind": "announce", "status": {"id": "9"}}
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   reaction_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_reactions": 4,
                                                                                "reacted": True}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row], "https://x/actors/me")

    assert result[0].reblog.favourites_count == 4
    assert result[0].favourites_count == 4
    assert result[0].favourited is True


def _counted(emoji, count, reacted=False):
    return {"object_url": "https://x/notes/5", "emoji": emoji, "n_of_reactions": count, "reacted": reacted}


def test_emoji_reactions_are_sorted_by_count_then_by_emoji():
    result = service._emoji_reactions([_counted("🐶", 1), _counted("🎉", 3), _counted("🍀", 1)], "❤️")

    assert [entry["name"] for entry in result] == ["🎉", "🍀", "🐶"]


def test_an_emojiless_reaction_is_counted_as_the_default_emoji():
    result = service._emoji_reactions([_counted("", 2)], "❤️")

    assert result == [{"name": "❤️", "count": 2, "me": False}]


def test_an_emojiless_reaction_is_merged_into_an_explicit_default():
    result = service._emoji_reactions([_counted("", 2), _counted("❤️", 3, reacted=True)], "❤️")

    assert result == [{"name": "❤️", "count": 5, "me": True}]


def test_the_own_flag_survives_the_merge_from_either_side():
    result = service._emoji_reactions([_counted("", 1, reacted=True), _counted("❤️", 1)], "❤️")

    assert result[0]["me"] is True


@pytest.mark.asyncio
async def test_make_statuses_carries_the_breakdown_under_pleroma():
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   reaction_breakdown=AsyncMock(return_value={"https://x/notes/5": [_counted("🎉", 2, True)]}))
    cached, storage = _patches(store)

    with cached, storage, Cfg({"profed": {"run": "api"}, "api": {"default_reaction_emoji": "❤️"}}):
        result = await service.make_statuses([_row({"id": "5"})], "https://x/actors/me")

    assert result[0].pleroma["emoji_reactions"] == [{"name": "🎉", "count": 2, "me": True}]


@pytest.mark.asyncio
async def test_a_status_without_reactions_carries_an_empty_breakdown():
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["emoji_reactions"] == []


@pytest.mark.asyncio
async def test_a_local_status_is_marked_as_local():
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["local"] is True


@pytest.mark.asyncio
async def test_a_remote_status_is_not_marked_as_local():
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: False):
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["local"] is False


@pytest.mark.asyncio
async def test_a_top_level_post_has_no_replied_acct():
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["in_reply_to_account_acct"] is None


@pytest.mark.asyncio
async def test_a_reply_carries_the_acct_of_the_replied_account():
    row = {**_row({"id": "5"}),
           "parent_content": {"status": {"content": "<p>original</p>"},
                              "actor": "https://x/actors/bob"}}
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([row])

    assert result[0].pleroma["in_reply_to_account_acct"] == result[0].reply_to.account.acct

