# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.models.activity_pub.activity_streams import ActivityStreamsObject
from profed.models.activity_pub.person import Person
from profed.models import UserProfile

 
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

def test_person_from_user_with_avatar_uses_large_variant():
    profile = UserProfile(username=    "alice",
                          avatar_url=  "https://cdn.example.com/ab/abcdef")

    person = Person.from_user(profile)

    assert person.icon == {"type": "Image",
                           "url":  "https://cdn.example.com/ab/abcdef"}


def test_person_from_user_with_header_uses_wide_variant():
    profile = UserProfile(username=    "alice",
                          header_url=  "https://cdn.example.com/cd/cdef12")

    person = Person.from_user(profile)

    assert person.image == {"type": "Image",
                            "url":  "https://cdn.example.com/cd/cdef12"}


def test_person_from_user_without_avatar_has_no_icon():
    profile = UserProfile(username="alice")

    person = Person.from_user(profile)

    assert person.icon  is None
    assert person.image is None

