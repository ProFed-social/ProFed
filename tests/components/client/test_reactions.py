# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.client import reactions


def test_an_empty_history_gives_no_counts_and_no_tone():
    assert reactions.from_history({}) == {"reactions": {}, "tone": ""}


def test_the_counts_are_taken_over_per_emoji():
    payload = {"counts": [{"emoji": "🎉", "n_of_uses": 3}, {"emoji": "🐶", "n_of_uses": 1}], "last_toned": None}

    assert reactions.from_history(payload)["reactions"] == {"🎉": 3, "🐶": 1}


def test_the_counts_of_the_toned_variants_land_on_their_base_form():
    payload = {"counts": [{"emoji": "👍", "n_of_uses": 2},
                          {"emoji": "👍🏽", "n_of_uses": 3},
                          {"emoji": "👍🏿", "n_of_uses": 1}]}

    assert reactions.from_history(payload)["reactions"] == {"👍": 6}


def test_the_tone_comes_from_the_last_toned_reaction():
    assert reactions.from_history({"last_toned": "👍🏽"})["tone"] == "medium"


def test_without_a_toned_reaction_there_is_no_tone():
    assert reactions.from_history({"counts": [], "last_toned": None})["tone"] == ""


def test_the_quick_access_takes_the_five_most_used_emoji():
    counts = {"🎉": 2, "👍": 9, "👏": 4, "💡": 1, "😂": 5, "🐶": 7}

    assert reactions.quick_access(counts, ["❤️"] * 5) == ["👍", "🐶", "😂", "👏", "🎉"]


def test_the_quick_access_breaks_a_tie_by_the_emoji_itself():
    assert reactions.quick_access({"👍": 1, "🎉": 1}, ["💡"] * 5)[:2] == ["🎉", "👍"]


def test_the_quick_access_has_as_many_places_as_the_default_list():
    assert reactions.quick_access({"🎉": 3, "👍": 2, "👏": 1}, ["💡", "😂"]) == ["🎉", "👍"]


def test_the_quick_access_fills_up_from_the_defaults():
    assert reactions.quick_access({"🐶": 3}, ["👍", "❤️", "👏", "💡", "😂"]) == ["🐶", "👍", "❤️", "👏", "💡"]


def test_the_quick_access_does_not_repeat_an_emoji_it_already_has():
    assert reactions.quick_access({"👏": 3}, ["👍", "❤️", "👏", "💡", "😂"]) == ["👏", "👍", "❤️", "💡", "😂"]


def test_without_any_history_the_quick_access_is_the_default_list():
    assert reactions.quick_access({}, ["👍", "❤️", "👏", "💡", "😂"]) == ["👍", "❤️", "👏", "💡", "😂"]


def test_a_first_reaction_starts_its_count():
    assert reactions.after_react({"reactions": {}, "tone": ""}, "🎉", "")["reactions"] == {"🎉": 1}


def test_a_further_reaction_counts_its_base_form_up():
    state = {"reactions": {"👍": 4}, "tone": ""}

    assert reactions.after_react(state, "👍🏽", "")["reactions"] == {"👍": 5}


def test_a_change_counts_the_old_one_down_and_the_new_one_up():
    state = {"reactions": {"👍": 4, "🎉": 1}, "tone": ""}

    assert reactions.after_react(state, "🎉", "👍")["reactions"] == {"👍": 3, "🎉": 2}


def test_reacting_with_the_same_emoji_again_changes_no_count():
    state = {"reactions": {"🎉": 2}, "tone": ""}

    assert reactions.after_react(state, "🎉", "🎉")["reactions"] == {"🎉": 2}


def test_a_change_within_one_base_form_changes_no_count():
    state = {"reactions": {"👍": 2}, "tone": ""}

    assert reactions.after_react(state, "👍🏽", "👍")["reactions"] == {"👍": 2}


def test_a_toned_reaction_sets_the_tone():
    assert reactions.after_react({"reactions": {}, "tone": "light"}, "👍🏿", "")["tone"] == "dark"


def test_an_untoned_reaction_keeps_the_tone():
    assert reactions.after_react({"reactions": {}, "tone": "medium"}, "🎉", "")["tone"] == "medium"


def test_taking_a_reaction_back_counts_its_base_form_down():
    state = {"reactions": {"👍": 4, "🎉": 1}, "tone": ""}

    assert reactions.after_unreact(state, "👍🏽")["reactions"] == {"👍": 3, "🎉": 1}


def test_the_last_use_of_an_emoji_drops_it_from_the_counts():
    assert reactions.after_unreact({"reactions": {"🎉": 1}, "tone": ""}, "🎉")["reactions"] == {}


def test_taking_a_reaction_back_keeps_the_tone():
    assert reactions.after_unreact({"reactions": {"👍": 1}, "tone": "medium"}, "👍")["tone"] == "medium"

