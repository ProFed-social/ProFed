# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.federation.audience import PUBLIC, recipients_of, visibility_of


ALICE = "https://example.com/actors/alice"

BOB = "https://r.example/users/bob"


def _create(**addressing):
    return {"id": f"{ALICE}#create/1",
            "type": "Create",
            "actor": ALICE,
            "object": {"id": f"{ALICE}/notes/1", **addressing}}


def test_the_public_collection_makes_it_public():
    assert visibility_of(_create(to=[PUBLIC], cc=[f"{ALICE}/followers"])) == "public"


def test_the_public_collection_in_cc_still_makes_it_public():
    assert visibility_of(_create(to=[f"{ALICE}/followers"], cc=[PUBLIC])) == "public"


def test_the_authors_followers_alone_make_it_followers_only():
    assert visibility_of(_create(to=[f"{ALICE}/followers"], cc=[])) == "followers"


def test_named_actors_alone_make_it_direct():
    assert visibility_of(_create(to=[BOB], cc=[])) == "direct"


def test_another_actors_followers_do_not_make_it_followers_only():
    assert visibility_of(_create(to=[f"{BOB}/followers"], cc=[])) == "direct"


def test_the_addressing_of_the_activity_counts_too():
    assert visibility_of({"type": "Create", "actor": ALICE, "to": [PUBLIC], "object": {"id": "x"}}) == "public"


def test_an_activity_without_an_inner_object_is_read_as_well():
    assert visibility_of({"type": "Follow", "actor": ALICE, "to": [BOB], "object": BOB}) == "direct"


def test_the_recipients_are_the_named_actors():
    assert recipients_of(_create(to=[BOB], cc=[f"{ALICE}/followers", PUBLIC])) == [BOB]


def test_the_recipients_are_sorted_and_free_of_duplicates():
    assert recipients_of({"type": "Create",
                          "actor": ALICE,
                          "to": [BOB],
                          "object": {"id": "x", "to": [BOB], "cc": ["https://a.test/z"]}}) == \
           ["https://a.test/z", BOB]


def test_a_post_to_nobody_has_no_recipients():
    assert recipients_of(_create(to=[PUBLIC], cc=[f"{ALICE}/followers"])) == []

