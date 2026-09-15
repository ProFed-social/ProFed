# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.incoming_activities_topic import is_reaction


def test_a_like_is_a_reaction():
    assert is_reaction("Like", {}) is True


def test_an_emoji_react_is_a_reaction():
    assert is_reaction("EmojiReact", {}) is True


def test_a_post_is_not_a_reaction():
    assert is_reaction("Create", {}) is False


def test_an_undone_like_is_a_reaction():
    assert is_reaction("Undo", {"object": {"id": "https://r/1", "type": "Like"}}) is True


def test_an_undone_emoji_react_is_a_reaction():
    assert is_reaction("Undo", {"object": {"id": "https://r/1", "type": "EmojiReact"}}) is True


def test_an_undone_boost_is_not_a_reaction():
    assert is_reaction("Undo", {"object": {"id": "https://r/1", "type": "Announce"}}) is False


def test_an_undo_that_names_only_an_id_is_not_a_reaction():
    assert is_reaction("Undo", {"object": "https://r/1"}) is False


def test_an_undo_without_an_object_is_not_a_reaction():
    assert is_reaction("Undo", {}) is False

