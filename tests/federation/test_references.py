# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import Mock
from profed.federation import references


BOOSTED = {"id": "https://remote/notes/orig",
           "type": "Note",
           "attributedTo": "https://remote/carol",
           "content": "hi",
           "published": "2026-01-01T00:00:00Z"}

PARENT = {"id": "https://remote/notes/parent",
          "type": "Note",
          "attributedTo": "https://remote/carol",
          "content": "p",
          "published": "2026-02-01T00:00:00Z"}

EMITTED = "2026-05-01T00:00:00Z"


def _run(activity, object_id, event_type):
    enqueue = Mock()
    result = references.flatten_references(activity, object_id, event_type, EMITTED, None, enqueue)
    return result, enqueue


def test_a_boost_by_url_enqueues_the_target_and_flattens_to_url():
    activity = {"actor": "https://remote/bob", "object": "https://remote/notes/orig"}

    result, enqueue = _run(activity, "https://remote/announce/1", "Announce")

    enqueue.assert_called_once_with("https://remote/notes/orig", "https://remote/announce/1", None, EMITTED, None)
    assert result["object"] == "https://remote/notes/orig"


def test_an_embedded_boost_enqueues_with_the_objects_version_and_flattens_to_url():
    activity = {"actor": "https://remote/bob", "object": BOOSTED}

    result, enqueue = _run(activity, "https://remote/announce/1", "Announce")

    enqueue.assert_called_once_with("https://remote/notes/orig",
                                    "https://remote/announce/1",
                                    "2026-01-01T00:00:00Z",
                                    EMITTED,
                                    None)
    assert result["object"] == "https://remote/notes/orig"


def test_a_reply_by_url_enqueues_the_parent_and_keeps_the_note():
    note = {"id": "https://remote/notes/2",
            "type": "Note",
            "attributedTo": "https://remote/bob",
            "content": "re",
            "inReplyTo": "https://remote/notes/parent"}

    activity = {"actor": "https://remote/bob", "object": note}

    result, enqueue = _run(activity, "https://remote/create/1", "Create")
    enqueue.assert_called_once_with("https://remote/notes/parent", "https://remote/notes/2", None, EMITTED, None)
    assert result["object"]["inReplyTo"] == "https://remote/notes/parent"
    assert result["object"]["content"] == "re"


def test_an_embedded_reply_parent_enqueues_with_version_and_flattens_to_its_url():
    note = {"id": "https://remote/notes/2",
            "type": "Note",
            "attributedTo": "https://remote/bob",
            "content": "re",
            "inReplyTo": PARENT}

    activity = {"actor": "https://remote/bob", "object": note}

    result, enqueue = _run(activity, "https://remote/create/1", "Create")
    enqueue.assert_called_once_with("https://remote/notes/parent",
                                    "https://remote/notes/2",
                                    "2026-02-01T00:00:00Z",
                                    EMITTED,
                                    None)
    assert result["object"]["inReplyTo"] == "https://remote/notes/parent"


def test_an_ordinary_post_enqueues_nothing():
    note = {"id": "https://remote/notes/3", "type": "Note", "attributedTo": "https://remote/bob", "content": "hi"}
    activity = {"actor": "https://remote/bob", "object": note}

    result, enqueue = _run(activity, "https://remote/create/1", "Create")

    enqueue.assert_not_called()
    assert result == activity

