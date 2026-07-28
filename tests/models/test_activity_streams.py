# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from profed.models.activity_pub.activity_streams import ActivityStreamsObject, AnnounceReference, ReplyToReference
from profed.models.activity_pub.object import Note
from profed.models.activity_pub.person import Person
from profed.models import UserProfile, MediaReference


def test_default_context_set_when_empty():
    obj = ActivityStreamsObject(id="https://example.com/1", type="Note")

    assert obj.context == ["https://www.w3.org/ns/activitystreams"]


def test_context_not_overwritten_when_provided():
    obj = ActivityStreamsObject(id="https://example.com/1",
                                type="Note",
                                **{"@context": ["https://custom.example/ns"]})

    assert obj.context == ["https://custom.example/ns"]


def test_context_coerced_from_string():
    obj = ActivityStreamsObject(id="https://example.com/1",
                                type="Note",
                                **{"@context": "https://www.w3.org/ns/activitystreams"})

    assert obj.context == ["https://www.w3.org/ns/activitystreams"]


def test_person_gets_extended_context():
    p = Person(id="https://example.com/actors/alice",
               type="Person",
               preferredUsername="alice",
               inbox="https://example.com/actors/alice/inbox",
               outbox="https://example.com/actors/alice/outbox")

    assert "https://www.w3.org/ns/activitystreams" in p.context
    assert any(isinstance(e, dict) and "profed" in e for e in p.context)


def test_person_context_not_overwritten_when_provided():
    p = Person(id="https://example.com/actors/alice",
               type="Person",
               preferredUsername="alice",
               inbox="https://example.com/actors/alice/inbox",
               outbox="https://example.com/actors/alice/outbox",
               **{"@context": ["https://custom.example/ns"]})

    assert p.context == ["https://custom.example/ns"]

def test_person_from_user_with_avatar_uses_large_variant(fake_media_storage):
    profile = UserProfile(username= "alice",
                          avatar=   MediaReference(media_id="abcdef", variants={"large", "small"}))

    person = Person.from_user(profile)

    assert person.icon == {"type": "Image",
                           "url": "https://fake.example.com/abcdef_large"}


def test_person_from_user_with_header_uses_wide_variant(fake_media_storage):
    profile = UserProfile(username= "alice",
                          header=   MediaReference(media_id="cdef12", variants={"wide"}))

    person = Person.from_user(profile)

    assert person.image == {"type": "Image",
                            "url": "https://fake.example.com/cdef12_wide"}


def test_person_from_user_avatar_without_variant_falls_back_to_original(fake_media_storage):
    profile = UserProfile(username= "alice",
                          avatar=   MediaReference(media_id="abcdef", variants=set()))

    person = Person.from_user(profile)

    assert person.icon == {"type": "Image",
                           "url":  "https://fake.example.com/abcdef"}


def test_person_from_user_without_avatar_has_no_icon():
    profile = UserProfile(username="alice")

    person = Person.from_user(profile)

    assert person.icon  is None
    assert person.image is None


def _note(**extra):
    return Note(id="https://x.example/n",
                attributedTo="https://x.example/@a",
                content="hi",
                published="2026-01-01T00:00:00Z",
                **extra)

def _announce(obj):
    return ActivityStreamsObject(id="https://x.example/a", type="Announce", actor="https://x.example/@b", object=obj)


def _create(obj):
    return ActivityStreamsObject(id="https://x.example/c", type="Create", actor="https://x.example/@a", object=obj)


def test_an_ordinary_post_references_nothing():
    assert _note().referenced_objects() == set()


def test_a_reply_references_its_parent():
    reply = _note(inReplyTo="https://x.example/parent")

    assert reply.referenced_objects() == {ReplyToReference(url="https://x.example/parent")}


def test_a_boost_references_the_announced_url():
    assert _announce("https://x.example/boosted").referenced_objects() == \
            {AnnounceReference(url="https://x.example/boosted")}


def test_a_boost_and_a_reply_to_the_same_url_are_distinct_references():
    assert _announce("https://x.example/same").referenced_objects() != \
            _note(inReplyTo="https://x.example/same").referenced_objects()


def test_a_create_around_a_plain_note_references_nothing():
   assert _create({"id": "https://x.example/n", "type": "Note", "content": "hi"}).referenced_objects() == set()


def test_a_create_finds_its_wrapped_reply():
    create = ActivityStreamsObject(id="https://x.example/c",
                                   type="Create",
                                   actor="https://x.example/@a",
                                   object={"id": "https://x.example/n",
                                           "type": "Note",
                                           "inReplyTo": "https://x.example/parent"})

    assert create.referenced_objects() == {ReplyToReference(url="https://x.example/parent")}



def test_an_embedded_reference_uses_its_id():
    boost = _announce({"id": "https://x.example/boosted", "type": "Note"})

    assert boost.referenced_objects() == {AnnounceReference(url="https://x.example/boosted")}


def test_an_embedded_reference_carries_the_object():
    boost = _announce({"id": "https://x.example/boosted", "type": "Note", "content": "hi"})
    reference = next(iter(boost.referenced_objects()))
    assert reference.embedded == {"id": "https://x.example/boosted", "type": "Note", "content": "hi"}


def test_a_url_reference_carries_no_object():
    reference = next(iter(_announce("https://x.example/boosted").referenced_objects()))
    assert reference.embedded is None


def test_two_references_are_equal_regardless_of_the_carried_object():
    assert (AnnounceReference(url="https://x.example/b", embedded={"id": "https://x.example/b"}) == \
            AnnounceReference(url="https://x.example/b")) 


def test_a_boosted_reply_yields_both_targets():
    boost = _announce({"id": "https://x.example/boosted", "type": "Note", "inReplyTo": "https://x.example/grandparent"})

    assert boost.referenced_objects() == {AnnounceReference(url="https://x.example/boosted"),
                                          ReplyToReference(url="https://x.example/grandparent")}

def test_duplicate_references_are_collapsed():
    boost = _announce(["https://x.example/same", "https://x.example/same"])

    assert boost.referenced_objects() == {AnnounceReference(url="https://x.example/same")}


def test_nesting_below_the_direct_level_is_left_to_reprocessing():
    create = _create({"id": "https://x.example/inner",
                      "type": "Create",
                      "object": {"id": "https://x.example/n",
                                 "type": "Note",
                                 "inReplyTo": "https://x.example/deep-parent"}})
    assert create.referenced_objects() == set()

