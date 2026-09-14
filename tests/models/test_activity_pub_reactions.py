# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from pydantic import ValidationError

from profed.models.activity_pub import EmojiReactActivity, LikeActivity, UndoEmojiReactActivity


def _react(**kw):
    return EmojiReactActivity(id="https://x/actors/alice#react/1",
                              actor="https://x/actors/alice",
                              object="https://r.example/notes/7",
                              **kw)


def test_an_emoji_react_carries_its_type():
    assert _react(content="🎉").type == "EmojiReact"


def test_an_emoji_react_needs_its_emoji():
    with pytest.raises(ValidationError):
        _react()


def test_an_emoji_react_rejects_an_empty_emoji():
    with pytest.raises(ValidationError):
        _react(content="")


def test_an_emoji_react_keeps_its_addressing():
    assert _react(content="🎉", to=["https://r.example/bob"]).to == ["https://r.example/bob"]


def test_an_undone_emoji_react_wraps_the_reaction():
    undone = UndoEmojiReactActivity(id="https://x/actors/alice#undo/1",
                                    actor="https://x/actors/alice",
                                    to=["https://r.example/bob"],
                                    object=_react(content="🎉"))

    assert undone.type == "Undo"
    assert undone.object.type == "EmojiReact"
    assert undone.object.content == "🎉"


def test_an_undone_emoji_react_does_not_take_a_like():
    with pytest.raises(ValidationError):
        UndoEmojiReactActivity(id="https://x/actors/alice#undo/1",
                               actor="https://x/actors/alice",
                               object=LikeActivity(id="https://x/actors/alice#like/1",
                                                   actor="https://x/actors/alice",
                                                   object="https://r.example/notes/7"))

