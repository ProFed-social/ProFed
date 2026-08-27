# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.actor_extractor import extract


PUBLIC = "https://www.w3.org/ns/activitystreams#Public"


def _note(**overrides):
    return {"type": "Create",
            "actor": "https://a.test/actors/alice",
            "object": {"id": "https://a.test/notes/1",
                       "type": "Note",
                       **overrides}}


def test_actor_urls_take_the_actor():
    assert extract.actor_urls(_note()) == {"https://a.test/actors/alice"}


def test_actor_urls_take_attributed_to():
    assert "https://b.test/actors/bob" in extract.actor_urls(_note(attributedTo="https://b.test/actors/bob"))


def test_actor_urls_take_mention_hrefs():
    urls = extract.actor_urls(_note(tag=[{"type": "Mention",
                                          "href": "https://c.test/actors/carol",
                                          "name": "@carol@c.test"}]))

    assert "https://c.test/actors/carol" in urls


def test_actor_urls_ignore_tags_that_are_no_mentions():
    urls = extract.actor_urls(_note(tag=[{"type": "Hashtag", "href": "https://a.test/tags/x", "name": "#x"}]))

    assert urls == {"https://a.test/actors/alice"}


def test_actor_urls_take_addressed_actors():
    urls = extract.actor_urls(_note(to=[PUBLIC], cc=["https://b.test/actors/bob"]))

    assert "https://b.test/actors/bob" in urls


def test_actor_urls_ignore_the_public_collection():
    assert PUBLIC not in extract.actor_urls(_note(to=[PUBLIC]))


def test_actor_urls_ignore_a_followers_collection():
    urls = extract.actor_urls(_note(cc=["https://a.test/actors/alice/followers"]))

    assert urls == {"https://a.test/actors/alice"}


def test_actor_urls_take_the_target_of_a_follow():
    activity = {"type": "Follow",
                "actor": "https://a.test/actors/alice",
                "object": "https://d.test/actors/dave"}

    assert extract.actor_urls(activity) == {"https://a.test/actors/alice", "https://d.test/actors/dave"}


def test_actor_urls_take_the_target_of_an_undone_follow():
    activity = {"type": "Undo",
                "actor": "https://a.test/actors/alice",
                "object": {"type": "Follow", "object": "https://e.test/actors/eve"}}

    assert "https://e.test/actors/eve" in extract.actor_urls(activity)


def test_actor_urls_leave_the_object_of_a_delete_alone():
    activity = {"type": "Delete",
                "actor": "https://a.test/actors/alice",
                "object": "https://a.test/notes/1"}

    assert extract.actor_urls(activity) == {"https://a.test/actors/alice"}


def test_actor_urls_ignore_anything_that_is_no_https_url():
    activity = {"type": "Create", "actor": "acct:alice@a.test", "object": {"attributedTo": 17}}

    assert extract.actor_urls(activity) == set()


def test_actor_urls_of_an_empty_activity_are_empty():
    assert extract.actor_urls({}) == set()


def test_accts_come_from_mention_names():
    activity = _note(tag=[{"type": "Mention",
                           "href": "https://c.test/actors/carol",
                           "name": "@carol@c.test"}])

    assert extract.accts(activity) == {"carol@c.test"}


def test_accts_ignore_a_name_without_a_domain():
    activity = _note(tag=[{"type": "Mention", "href": "https://a.test/actors/alice", "name": "@alice"}])

    assert extract.accts(activity) == set()


def test_accts_of_an_activity_without_mentions_are_empty():
    assert extract.accts(_note()) == set()

