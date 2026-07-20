# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.activity_pub import Activity, CreateActivity, Note


def _note(**kw):
    return Note(id="https://x/n", attributedTo="https://x/bob",
                content="hi", published="2026-01-01", **kw)


def test_note_and_activity_declare_addressing_fields():
    assert {"tag", "cc"} <= set(Note.model_fields)
    assert "cc" in Activity.model_fields


def test_note_defaults_tag_and_cc_to_empty():
    note = _note()

    assert note.tag == []
    assert note.cc == []


def test_create_activity_defaults_cc_to_none():
    activity = CreateActivity(id="https://x/a", actor="https://x/bob", object="https://x/n")

    assert activity.cc is None

