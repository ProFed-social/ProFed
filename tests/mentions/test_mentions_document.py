# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed import mentions
from profed.sanitize import as2_html_fields


ACTIVITY = {"type": "Create",
            "object": {"type": "Note",
                       "id": "https://x/notes/1",
                       "content": "hi @dave@r.io",
                       "summary": "cw @bob@r.io",
                       "published": "2026-01-01"}}

RESOLVED = [("dave", "r.io", "dave@r.io", "https://r.io/dave"),
            ("bob", "r.io", "bob@r.io", "https://r.io/bob")]


def test_collect_gathers_content_and_summary():
    assert mentions.collect_html_texts(ACTIVITY, as2_html_fields) == \
        ["hi @dave@r.io", "cw @bob@r.io"]


def test_collect_gathers_nested_resume():
    payload = {"type": "Person",
               "resume": {"content": "@alice hire me", "description": "ref @bob"}}
    assert mentions.collect_html_texts(payload, as2_html_fields) == \
        ["@alice hire me", "ref @bob"]


def test_collect_gathers_langmap_values():
    payload = {"type": "Note", "contentMap": {"en": "@dave hi", "de": "@dave hallo"}}
    assert mentions.collect_html_texts(payload, as2_html_fields) == \
        ["@dave hi", "@dave hallo"]


def test_collect_ignores_non_html_fields():
    assert mentions.collect_html_texts({"id": "https://x/1", "type": "Note"},
                                       as2_html_fields) == []


def test_linkify_document_linkifies_html_fields():
    out = mentions.linkify_document(ACTIVITY, RESOLVED, as2_html_fields)
    assert out["object"]["content"] == \
        'hi <a class="u-url mention" href="https://r.io/dave">@dave</a>'
    assert out["object"]["summary"] == \
        'cw <a class="u-url mention" href="https://r.io/bob">@bob</a>'


def test_linkify_document_leaves_non_html_untouched():
    out = mentions.linkify_document(ACTIVITY, RESOLVED, as2_html_fields)
    assert out["object"]["id"] == "https://x/notes/1"
    assert out["object"]["type"] == "Note"
    assert out["object"]["published"] == "2026-01-01"


def test_linkify_document_handles_nested_resume():
    payload = {"type": "Person",
               "resume": {"content": "@dave@r.io hi", "description": "plain text"}}
    out = mentions.linkify_document(payload, RESOLVED, as2_html_fields)
    assert out["resume"]["content"] == \
        '<a class="u-url mention" href="https://r.io/dave">@dave</a> hi'
    assert out["resume"]["description"] == "plain text"

