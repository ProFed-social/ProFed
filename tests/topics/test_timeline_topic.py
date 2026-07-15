# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from profed.topics.timeline_topic import (validate_timeline_event,
                                          validate_timeline_snapshot_item)


PAYLOAD = {"username": "alice",
           "activity": {"id": "https://remote/notes/1", "actor": "https://remote/bob"}}


@pytest.mark.parametrize("verb", ["Create", "Update", "Delete", "Announce"])
def test_timeline_verbs_return_payload(verb):
    payload = validate_timeline_event(verb, PAYLOAD)

    assert payload is not None
    assert payload["username"] == "alice"


@pytest.mark.parametrize("verb", ["Follow", "Accept", "Reject", "Undo", "Like", "Block", "Tick"])
def test_non_timeline_verbs_are_rejected(verb):
    assert validate_timeline_event(verb, PAYLOAD) is None


def test_payload_must_be_a_dict():
    assert validate_timeline_event("Create", "nope") is None


def test_missing_username_is_rejected():
    assert validate_timeline_event("Create", {"activity": {"id": "https://remote/notes/1"}}) is None


def test_empty_username_is_rejected():
    assert validate_timeline_event("Create", {"username": "", "activity": {}}) is None


def test_missing_activity_is_rejected():
    assert validate_timeline_event("Create", {"username": "alice"}) is None


def test_snapshot_items_are_not_supported():
    assert validate_timeline_snapshot_item({"username": "alice"}) is None

