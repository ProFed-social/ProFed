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


def test_a_tone_is_inserted_before_a_hair_modifier():
    assert emoji.grid("light")["People & Body"][emoji.groups()["People & Body"].index("👨\u200d🦰")] == "👨🏻\u200d🦰"


def test_a_toned_grid_leaves_emoji_without_variants_alone():
    assert emoji.grid("light")["Activities"] == emoji.groups()["Activities"]


def test_a_toned_grid_keeps_the_group_order_and_length():
    plain, toned = emoji.groups(), emoji.grid("dark")

    assert list(plain) == list(toned)
    assert all(len(plain[group]) == len(toned[group]) for group in plain)


def test_every_toned_emoji_is_one_the_data_file_knows():
    known = {choice
             for choices in emoji._grouped(emoji.DATA.read_text(encoding="utf-8").splitlines()).values()
             for choice in choices}

    assert all(choice in known for choices in emoji.grid("light").values() for choice in choices)


def test_a_base_form_with_a_variation_selector_still_finds_its_variant():
    people = emoji.groups()["People & Body"]

    assert emoji.grid("medium")["People & Body"][people.index("\u270C\uFE0F")] == "\u270C\U0001F3FD"


def test_a_variant_that_keeps_its_own_selector_is_found_too():
    people = emoji.groups()["People & Body"]

    assert emoji.grid("light")["People & Body"][people.index("🧔\u200d♂\uFE0F")] == "🧔🏻\u200d♂\uFE0F"

