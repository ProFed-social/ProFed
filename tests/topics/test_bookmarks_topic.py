# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.topics.bookmarks_topic import (bookmark_id,
                                           publish_bookmark,
                                           validate_bookmarks_event,
                                           validate_bookmarks_snapshot_item)


NOTE = "https://remote.example/notes/7"

ALICE = "https://example.com/actors/alice"

MARK = {"actor_url": ALICE, "object_url": NOTE}


def test_adding_a_bookmark_is_an_event():
    assert validate_bookmarks_event("added", MARK) == MARK


def test_removing_a_bookmark_is_an_event():
    assert validate_bookmarks_event("removed", MARK) == MARK


def test_another_verb_is_no_bookmark_event():
    assert validate_bookmarks_event("moved", MARK) is None


def test_a_payload_that_is_not_a_dict_is_refused():
    assert validate_bookmarks_event("added", [NOTE]) is None


def test_a_bookmark_without_an_owner_is_refused():
    assert validate_bookmarks_event("added", {"object_url": NOTE}) is None


def test_a_bookmark_without_an_object_is_refused():
    assert validate_bookmarks_event("added", {"actor_url": ALICE}) is None


def test_an_empty_owner_is_no_owner():
    assert validate_bookmarks_event("added", {"actor_url": "", "object_url": NOTE}) is None


def test_other_fields_survive():
    event = validate_bookmarks_event("added", {**MARK, "folder": "later"})

    assert event["folder"] == "later"


def test_a_snapshot_item_names_its_owner_and_its_object():
    assert validate_bookmarks_snapshot_item(MARK) == MARK


def test_a_snapshot_item_without_an_object_is_refused():
    assert validate_bookmarks_snapshot_item({"actor_url": ALICE}) is None


def test_the_subject_combines_the_owner_and_the_object():
    assert bookmark_id(ALICE, NOTE) == f"{ALICE}|{NOTE}"


def test_two_users_bookmarking_the_same_note_are_two_subjects():
    assert bookmark_id(ALICE, NOTE) != bookmark_id("https://example.com/actors/bob", NOTE)


@pytest.mark.asyncio
async def test_publishing_names_the_pair_as_the_subject(fake_bus):
    await publish_bookmark("added", ALICE, NOTE)

    published = fake_bus.topic("bookmarks").published[0]
    assert published["event_type"] == "added"
    assert published["object_id"] == bookmark_id(ALICE, NOTE)
    assert published["payload"] == MARK


@pytest.mark.asyncio
async def test_removing_publishes_the_same_subject(fake_bus):
    await publish_bookmark("removed", ALICE, NOTE)

    assert fake_bus.topic("bookmarks").published[0]["object_id"] == bookmark_id(ALICE, NOTE)

