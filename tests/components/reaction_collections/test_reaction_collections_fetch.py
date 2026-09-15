# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.reaction_collections import fetch


NOTE = "https://remote.example/notes/7"

REACTIONS = f"{NOTE}/emojiReactions"

LIKES = f"{NOTE}/likes"


def _like(n, object_url=NOTE, **rest):
    return {"id": f"https://r.example/users/bob#react/{n}",
            "type": "Like",
            "actor": "https://r.example/users/bob",
            "object": object_url,
            "content": "🎉",
            **rest}


def test_emoji_reactions_come_before_likes():
    assert fetch.collection_url({"likes": LIKES, "emojiReactions": REACTIONS}) == REACTIONS


def test_likes_are_taken_when_there_are_no_emoji_reactions():
    assert fetch.collection_url({"likes": LIKES}) == LIKES


def test_an_embedded_collection_is_used_by_its_id():
    assert fetch.collection_url({"likes": {"id": LIKES, "type": "OrderedCollection"}}) == LIKES


def test_an_embedded_collection_without_an_id_is_no_use():
    assert fetch.collection_url({"likes": {"type": "OrderedCollection", "totalItems": 3}}) is None


def test_an_object_without_collections_has_nothing_to_fetch():
    assert fetch.collection_url({"id": NOTE, "type": "Note"}) is None


def test_the_total_is_read_when_it_is_a_count():
    assert fetch.total_of({"totalItems": 7}) == 7


def test_a_nonsense_total_is_ignored():
    assert fetch.total_of({"totalItems": -1}) is None
    assert fetch.total_of({"totalItems": "many"}) is None
    assert fetch.total_of({}) is None


def test_a_page_yields_its_items_and_the_next_url():
    page = {"orderedItems": [_like(1)], "next": f"{REACTIONS}?page=true&before=5"}

    items, nxt = fetch.page_of(page)

    assert items == [_like(1)]
    assert nxt == f"{REACTIONS}?page=true&before=5"


def test_a_page_may_use_items_instead_of_ordered_items():
    assert fetch.page_of({"items": [_like(1)]})[0] == [_like(1)]


def test_the_last_page_points_nowhere():
    assert fetch.page_of({"orderedItems": [_like(1)]})[1] is None


def test_entries_that_are_not_objects_are_dropped():
    assert fetch.page_of({"orderedItems": ["https://r.example/users/bob", None]})[0] == []


def test_a_collection_that_points_at_its_first_page_yields_no_items_yet():
    assert fetch.start_of({"totalItems": 3, "first": f"{REACTIONS}?page=true"}) == \
        ([], f"{REACTIONS}?page=true")


def test_an_embedded_first_page_is_read_right_away():
    collection = {"totalItems": 1, "first": {"orderedItems": [_like(1)], "next": None}}

    assert fetch.start_of(collection) == ([_like(1)], None)


def test_a_collection_that_carries_its_items_needs_no_page():
    assert fetch.start_of({"totalItems": 1, "orderedItems": [_like(1)]}) == ([_like(1)], None)


def test_a_reaction_on_this_object_counts():
    assert fetch.reactions_of([_like(1)], NOTE) == [_like(1)]


def test_an_emoji_react_counts_too():
    assert fetch.reactions_of([_like(1, type="EmojiReact")], NOTE) == [_like(1, type="EmojiReact")]


def test_a_reaction_on_another_object_is_not_ours():
    assert fetch.reactions_of([_like(1, object_url="https://elsewhere.example/notes/1")], NOTE) == []


def test_an_embedded_target_is_matched_by_its_id():
    assert fetch.reactions_of([_like(1, object=NOTE)], NOTE) == [_like(1, object=NOTE)]


def test_something_that_is_not_a_reaction_is_dropped():
    assert fetch.reactions_of([_like(1, type="Announce")], NOTE) == []


def test_a_reaction_without_an_actor_is_dropped():
    assert fetch.reactions_of([_like(1, actor="")], NOTE) == []


def test_a_reaction_without_an_id_is_dropped():
    assert fetch.reactions_of([{k: v for k, v in _like(1).items() if k != "id"}], NOTE) == []


def test_reading_stops_when_the_announced_total_is_reached():
    assert fetch.enough(seen=7, pages=1, total=7, max_pages=500) is True


def test_reading_goes_on_while_the_total_is_not_reached():
    assert fetch.enough(seen=3, pages=1, total=7, max_pages=500) is False


def test_reading_stops_at_the_page_limit_without_a_total():
    assert fetch.enough(seen=100, pages=500, total=None, max_pages=500) is True


def test_reading_goes_on_without_a_total_below_the_limit():
    assert fetch.enough(seen=100, pages=1, total=None, max_pages=500) is False


def test_more_than_announced_also_stops_the_reading():
    assert fetch.enough(seen=9, pages=1, total=7, max_pages=500) is True

