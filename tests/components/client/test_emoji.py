# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.client import emoji


def test_the_groups_keep_the_unicode_order():
    assert list(emoji.groups())[:3] == ["Smileys & Emotion", "People & Body", "Animals & Nature"]


def test_every_group_holds_emoji():
    assert all(group for group in emoji.groups().values())


def test_groups_that_hold_only_modifiers_are_left_out():
    assert "Component" not in emoji.groups()


def test_skin_tone_variants_are_not_listed_separately():
    assert not any(tone in choice
                   for choices in emoji.groups().values()
                   for choice in choices
                   for tone in emoji.TONES)


def test_a_tone_is_appended_where_the_emoji_allows_it():
    assert emoji.toned("\U0001F44D", "\U0001F3FD") == "\U0001F44D\U0001F3FD"


def test_a_tone_is_ignored_where_the_emoji_has_no_variants():
    assert emoji.toned("\U0001F389", "\U0001F3FD") == "\U0001F389"


def test_no_tone_leaves_the_emoji_untouched():
    assert emoji.toned("\U0001F44D", "") == "\U0001F44D"


def test_a_variation_selector_gives_way_to_the_tone():
    assert emoji.toned("\U0000270C\U0000FE0F", "\U0001F3FD") == "\U0000270C\U0001F3FD"
