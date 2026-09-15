# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.normalize_reactions import translator


REACTION = "https://remote.example/bob#react/3"


def _payload(**activity):
    return {"username": "alice",
            "activity": {"id": REACTION,
                         "actor": "https://remote.example/bob",
                         "object": "https://example.com/actors/alice/notes/7",
                         **activity}}


def _undo(**inner):
    return {"username": "alice",
            "activity": {"id": "https://remote.example/bob#undo/1",
                         "actor": "https://remote.example/bob",
                         "object": {"id": REACTION,
                                    "actor": "https://remote.example/bob",
                                    "object": "https://example.com/actors/alice/notes/7",
                                    **inner}}}


def _published(fake_bus):
    return fake_bus.topic("resolved_activities").published


@pytest.mark.asyncio
async def test_an_emoji_react_becomes_a_like(fake_bus):
    await translator._handle("EmojiReact", REACTION, _payload(type="EmojiReact", content="🎉"), 1)

    published = _published(fake_bus)[0]
    assert published["event_type"] == "Like"
    assert published["payload"]["activity"]["type"] == "Like"
    assert published["payload"]["activity"]["content"] == "🎉"


@pytest.mark.asyncio
async def test_a_misskey_reaction_moves_into_the_content(fake_bus):
    await translator._handle("Like", REACTION, _payload(type="Like", **{"_misskey_reaction": "🎉"}), 1)

    activity = _published(fake_bus)[0]["payload"]["activity"]
    assert activity["content"] == "🎉"
    assert "_misskey_reaction" not in activity


@pytest.mark.asyncio
async def test_a_bare_like_keeps_no_content(fake_bus):
    await translator._handle("Like", REACTION, _payload(type="Like"), 1)

    assert "content" not in _published(fake_bus)[0]["payload"]["activity"]


@pytest.mark.asyncio
async def test_something_that_is_not_an_emoji_is_dropped(fake_bus):
    await translator._handle("Like", REACTION, _payload(type="Like", content="<script>alert(1)</script>"), 1)

    activity = _published(fake_bus)[0]["payload"]["activity"]
    assert "content" not in activity
    assert activity["type"] == "Like"


@pytest.mark.asyncio
async def test_a_custom_shortcode_is_dropped(fake_bus):
    await translator._handle("EmojiReact", REACTION, _payload(type="EmojiReact", content=":blobcat:"), 1)

    assert "content" not in _published(fake_bus)[0]["payload"]["activity"]


@pytest.mark.asyncio
async def test_an_undone_reaction_is_normalized_inside(fake_bus):
    await translator._handle("Undo", "https://remote.example/bob#undo/1", _undo(type="EmojiReact", content="🎉"), 1)

    published = _published(fake_bus)[0]
    assert published["event_type"] == "Undo"
    assert published["payload"]["activity"]["object"]["type"] == "Like"
    assert published["payload"]["activity"]["object"]["id"] == REACTION


@pytest.mark.asyncio
async def test_an_undone_boost_is_not_ours(fake_bus):
    await translator._handle("Undo", "https://remote.example/bob#undo/2", _undo(type="Announce"), 1)

    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_an_undo_that_names_only_an_id_is_not_ours(fake_bus):
    payload = {"username": "alice",
               "activity": {"id": "https://remote.example/bob#undo/3", "object": REACTION}}

    await translator._handle("Undo", "https://remote.example/bob#undo/3", payload, 1)

    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_the_same_incoming_message_is_published_once(fake_bus):
    fake_bus.topic("resolved_activities", lookup_message_ids=True)
    await translator._handle("Like", REACTION, _payload(type="Like", content="🎉"), 5)
    await translator._handle("Like", REACTION, _payload(type="Like", content="🎉"), 5)

    assert len(_published(fake_bus)) == 1


@pytest.mark.asyncio
async def test_the_actor_and_the_target_survive(fake_bus):
    await translator._handle("EmojiReact", REACTION, _payload(type="EmojiReact", content="🎉"), 1)

    activity = _published(fake_bus)[0]["payload"]["activity"]
    assert activity["actor"] == "https://remote.example/bob"
    assert activity["object"] == "https://example.com/actors/alice/notes/7"
    assert activity["id"] == REACTION

