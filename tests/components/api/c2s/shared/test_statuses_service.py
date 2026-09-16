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
            "mastodon_id": status.get("id"),
            "status": status,
            "content": {"status": status, "actor": actor, "url": url, "mastodon_id": status.get("id")}}


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
async def test_make_statuses_resolves_in_reply_to_id_to_the_parent_mastodon_id(fake_bus):
    row = _row({"id": "5", "in_reply_to_id": "https://x/notes/1"})
    store = _store(mastodon_ids_for=AsyncMock(return_value={"https://x/notes/1": "99"}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id == "99"
    store.mastodon_ids_for.assert_awaited_once_with(["https://x/notes/1"])


@pytest.mark.asyncio
async def test_make_statuses_leaves_in_reply_to_id_none_when_the_parent_is_unknown(fake_bus):
    row = _row({"id": "5", "in_reply_to_id": "https://x/unknown"})
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id is None


@pytest.mark.asyncio
async def test_make_statuses_skips_the_lookup_for_a_top_level_post(fake_bus):
    row = _row({"id": "5", "in_reply_to_id": None})
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([row])

    assert result[0].in_reply_to_id is None
    store.mastodon_ids_for.assert_not_awaited()


@pytest.mark.asyncio
async def test_make_statuses_builds_a_reply_preview_from_the_parent_content(fake_bus):
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
async def test_make_statuses_leaves_reply_to_none_without_parent_content(fake_bus):
    store = _store(mastodon_ids_for=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].reply_to is None


@pytest.mark.asyncio
async def test_make_statuses_reads_the_boost_count_for_the_content_url(fake_bus):
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   boost_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_boosts": 3,
                                                                             "reblogged": False}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].reblogs_count == 3
    store.boost_stats.assert_awaited_once_with(["https://x/notes/5"], None)


@pytest.mark.asyncio
async def test_make_statuses_marks_the_viewers_own_boost(fake_bus):
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   boost_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_boosts": 1,
                                                                             "reblogged": True}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})], "https://x/actors/me")

    assert result[0].reblogged is True
    store.boost_stats.assert_awaited_once_with(["https://x/notes/5"], "https://x/actors/me")


@pytest.mark.asyncio
async def test_make_statuses_counts_an_unknown_content_url_as_zero(fake_bus):
    store = _store(mastodon_ids_for=AsyncMock(return_value={}), boost_stats=AsyncMock(return_value={}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].reblogs_count == 0
    assert result[0].reblogged is False


@pytest.mark.asyncio
async def test_a_boost_wrapper_repeats_the_counts_of_the_boosted_status(fake_bus):
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
async def test_make_statuses_reads_the_reaction_count_for_the_content_url(fake_bus):
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
async def test_make_statuses_marks_the_viewers_own_reaction(fake_bus):
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   reaction_stats=AsyncMock(return_value={"https://x/notes/5": {"n_of_reactions": 1,
                                                                                "reacted": True}}))
    cached, storage = _patches(store)

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})], "https://x/actors/me")

    assert result[0].favourited is True
    store.reaction_stats.assert_awaited_once_with(["https://x/notes/5"], "https://x/actors/me")


@pytest.mark.asyncio
async def test_a_boost_wrapper_repeats_the_reaction_counts(fake_bus):
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


def test_emoji_reactions_are_sorted_by_count_then_by_emoji(fake_bus):
    result = service._emoji_reactions([_counted("🐶", 1), _counted("🎉", 3), _counted("🍀", 1)], "❤️")

    assert [entry["name"] for entry in result] == ["🎉", "🍀", "🐶"]


def test_an_emojiless_reaction_is_counted_as_the_default_emoji(fake_bus):
    result = service._emoji_reactions([_counted("", 2)], "❤️")

    assert result == [{"name": "❤️", "count": 2, "me": False}]


def test_an_emojiless_reaction_is_merged_into_an_explicit_default(fake_bus):
    result = service._emoji_reactions([_counted("", 2), _counted("❤️", 3, reacted=True)], "❤️")

    assert result == [{"name": "❤️", "count": 5, "me": True}]


def test_the_own_flag_survives_the_merge_from_either_side(fake_bus):
    result = service._emoji_reactions([_counted("", 1, reacted=True), _counted("❤️", 1)], "❤️")

    assert result[0]["me"] is True


@pytest.mark.asyncio
async def test_make_statuses_carries_the_breakdown_under_pleroma(fake_bus):
    store = _store(mastodon_ids_for=AsyncMock(return_value={}),
                   reaction_breakdown=AsyncMock(return_value={"https://x/notes/5": [_counted("🎉", 2, True)]}))
    cached, storage = _patches(store)

    with cached, storage, Cfg({"profed": {"run": "api"}, "api": {"default_reaction_emoji": "❤️"}}):
        result = await service.make_statuses([_row({"id": "5"})], "https://x/actors/me")

    assert result[0].pleroma["emoji_reactions"] == [{"name": "🎉", "count": 2, "me": True}]


@pytest.mark.asyncio
async def test_a_status_without_reactions_carries_an_empty_breakdown(fake_bus):
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage:
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["emoji_reactions"] == []


@pytest.mark.asyncio
async def test_a_local_status_is_marked_as_local(fake_bus):
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["local"] is True


@pytest.mark.asyncio
async def test_a_remote_status_is_not_marked_as_local(fake_bus):
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: False):
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["local"] is False


@pytest.mark.asyncio
async def test_a_top_level_post_has_no_replied_acct(fake_bus):
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([_row({"id": "5"})])

    assert result[0].pleroma["in_reply_to_account_acct"] is None


@pytest.mark.asyncio
async def test_a_reply_carries_the_acct_of_the_replied_account(fake_bus):
    row = {**_row({"id": "5"}),
           "parent_content": {"status": {"content": "<p>original</p>"},
                              "actor": "https://x/actors/bob"}}
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([row])

    assert result[0].pleroma["in_reply_to_account_acct"] == result[0].reply_to.account.acct


@pytest.mark.asyncio
async def test_a_stale_id_in_the_stored_status_is_overruled_by_the_column(fake_bus):
    row = _row({"id": "424242"})
    row["content"]["mastodon_id"] = "999"
    row["mastodon_id"] = "999"
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([row])

    assert result[0].id == "999"


@pytest.mark.asyncio
async def test_a_boost_keeps_the_announce_id_outside_and_the_content_id_inside(fake_bus):
    note = {"id": "1", "content": "<p>hi</p>"}
    row = {"actor_url": "https://x/actors/carol",
           "kind": "announce",
           "mastodon_id": "500",
           "status": {"id": "stale", "content": ""},
           "content": {"status": note, "actor": "https://x/actors/bob",
                       "url": "https://x/notes/5", "mastodon_id": "424242"}}
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage, patch.object(service, "is_local_actor_url", lambda url: True):
        result = await service.make_statuses([row])

    assert result[0].id == "500"
    assert result[0].reblog.id == "424242"


@pytest.mark.asyncio
async def test_reading_asks_for_the_reactions_of_what_it_shows(fake_bus):
    rows = [_row({"id": "1"}, url="https://remote.example/notes/5"),
            _row({"id": "2"}, url="https://remote.example/notes/6")]
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage:
        await service.make_statuses(rows)

    asked = fake_bus.topic("reaction_refresh").published
    assert len(asked) == 1
    assert sorted(asked[0]["payload"]["object_urls"]) == ["https://remote.example/notes/5",
                                                          "https://remote.example/notes/6"]


@pytest.mark.asyncio
async def test_a_page_of_posts_is_one_question_not_twenty(fake_bus):
    rows = [_row({"id": str(n)}, url=f"https://remote.example/notes/{n}") for n in range(20)]
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage:
        await service.make_statuses(rows)

    assert len(fake_bus.topic("reaction_refresh").published) == 1


@pytest.mark.asyncio
async def test_the_same_post_twice_is_asked_for_once(fake_bus):
    rows = [_row({"id": "1"}), _row({"id": "1"})]
    cached, storage = _patches(_store(mastodon_ids_for=AsyncMock(return_value={})))

    with cached, storage:
        await service.make_statuses(rows)

    assert fake_bus.topic("reaction_refresh").published[0]["payload"]["object_urls"] == \
        ["https://x/notes/5"]

