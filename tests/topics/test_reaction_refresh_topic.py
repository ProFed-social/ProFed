# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.topics.reaction_refresh_topic import (publish_refresh,
                                                  validate_reaction_refresh_event,
                                                  validate_reaction_refresh_snapshot_item)


NOTE = "https://remote.example/notes/7"

OTHER = "https://remote.example/notes/8"


def test_a_request_keeps_its_urls():
    assert validate_reaction_refresh_event("requested", {"object_urls": [NOTE, OTHER]}) == \
        {"object_urls": [NOTE, OTHER]}


def test_another_verb_is_not_a_request():
    assert validate_reaction_refresh_event("finished", {"object_urls": [NOTE]}) is None


def test_a_payload_that_is_not_a_dict_is_refused():
    assert validate_reaction_refresh_event("requested", [NOTE]) is None


def test_a_request_without_urls_is_refused():
    assert validate_reaction_refresh_event("requested", {}) is None


def test_an_empty_list_is_refused():
    assert validate_reaction_refresh_event("requested", {"object_urls": []}) is None


def test_a_list_of_nothing_usable_is_refused():
    assert validate_reaction_refresh_event("requested", {"object_urls": ["", None, 7]}) is None


def test_unusable_entries_are_dropped():
    assert validate_reaction_refresh_event("requested", {"object_urls": [NOTE, "", None]}) == \
        {"object_urls": [NOTE]}


def test_the_same_url_is_asked_for_once():
    assert validate_reaction_refresh_event("requested", {"object_urls": [NOTE, OTHER, NOTE]}) == \
        {"object_urls": [NOTE, OTHER]}


def test_other_fields_survive():
    event = validate_reaction_refresh_event("requested", {"object_urls": [NOTE], "reason": "read"})

    assert event["reason"] == "read"


def test_the_topic_carries_no_snapshot():
    assert validate_reaction_refresh_snapshot_item({"object_urls": [NOTE]}) is None


@pytest.mark.asyncio
async def test_publishing_names_the_first_url_as_the_subject(fake_bus):
    await publish_refresh([NOTE, OTHER])

    published = fake_bus.topic("reaction_refresh").published[0]
    assert published["event_type"] == "requested"
    assert published["object_id"] == NOTE
    assert published["payload"] == {"object_urls": [NOTE, OTHER]}


@pytest.mark.asyncio
async def test_publishing_nothing_stays_quiet(fake_bus):
    await publish_refresh(["", None])

    assert fake_bus.topic("reaction_refresh").published == []


@pytest.mark.asyncio
async def test_publishing_drops_repeated_urls(fake_bus):
    await publish_refresh([NOTE, NOTE, OTHER])

    assert fake_bus.topic("reaction_refresh").published[0]["payload"]["object_urls"] == [NOTE, OTHER]

