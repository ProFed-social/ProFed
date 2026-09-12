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


def test_a_tone_is_applied_where_the_emoji_allows_it():
    assert emoji.toned("\U0001F44D", "medium") == "\U0001F44D\U0001F3FD"


def test_a_tone_is_ignored_where_the_emoji_has_no_variants():
    assert emoji.toned("\U0001F389", "medium") == "\U0001F389"


def test_no_tone_leaves_the_emoji_untouched():
    assert emoji.toned("\U0001F44D", "") == "\U0001F44D"


def test_a_variation_selector_gives_way_to_the_tone():
    assert emoji.toned("\U0000270C\U0000FE0F", "medium") == "\U0000270C\U0001F3FD"


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


def test_the_tone_of_a_toned_emoji_is_named():
    assert emoji.tone_of("👍🏽") == "medium"


def test_an_untoned_emoji_has_no_tone():
    assert emoji.tone_of("🎉") == ""


def test_the_base_of_a_toned_emoji_drops_the_tone():
    assert emoji.base_of("👍🏽") == "👍"


def test_the_base_of_a_toned_sequence_keeps_the_rest_of_it():
    assert emoji.base_of("👨🏻\u200d🦰") == "👨\u200d🦰"


def test_the_base_of_a_toned_emoji_regains_its_variation_selector():
    assert emoji.base_of("\u270C\U0001F3FD") == "\u270C\uFE0F"


def test_the_base_of_a_mixed_pair_drops_both_tones():
    assert emoji.base_of("🧑🏻\u200d🤝\u200d🧑🏿") == "🧑\u200d🤝\u200d🧑"


def test_an_untoned_emoji_is_its_own_base():
    assert emoji.base_of("🎉") == "🎉"


def test_an_unknown_reaction_is_its_own_base():
    assert emoji.base_of(":blobcat:") == ":blobcat:"


def test_a_name_from_the_data_file_resolves_to_its_emoji():
    assert emoji.from_text("waving hand: medium-dark skin tone") == "👋🏾"


def test_a_name_that_could_be_read_as_hexadecimal_gives_its_emoji():
    assert emoji.from_text("bed") == "🛏️"


def test_a_sequence_of_code_points_resolves_to_its_emoji():
    assert emoji.from_text("\\u1F468 \\u1F3FD \\u200D \\u1F9B2") == "👨🏽\u200d🦲"


def test_code_points_are_taken_with_any_of_the_usual_prefixes():
    assert all(emoji.from_text(text) == "👍" for text in ("1F44D", "\\u1F44D", "\\U1F44D", "U+1F44D", "u+1F44D"))


def test_an_emoji_resolves_to_itself():
    assert emoji.from_text("🧔🏻\u200d♀️") == "🧔🏻\u200d♀️"


def test_an_emoji_the_data_file_does_not_know_resolves_to_nothing():
    assert emoji.from_text("\u270C") == ""


def test_a_text_that_is_neither_a_name_nor_code_points_resolves_to_nothing():
    assert emoji.from_text("thumbs upp") == ""

