# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import mf2py
import pytest
from profed.components.client.templating import STANDARD_TEMPLATES, build_environment


STATUS = {"content": "<p>Hallo Welt</p>",
          "created_at": "2026-01-01T10:00:00.000Z",
          "url": "https://example.com/@alice/1",
          "uri": "https://example.com/actors/alice/notes/1",
          "reblogs_count": 2,
          "favourites_count": 5,
          "tags": [{"name": "python", "url": "https://example.com/tags/python"},
                   {"name": "fediverse", "url": "https://example.com/tags/fediverse"}],
          "account": {"url": "https://example.com/@alice",
                      "acct": "alice",
                      "display_name": "Alice",
                      "username": "alice",
                      "avatar": ""}}


def _render(status=STATUS, **context):
    environment = build_environment(STANDARD_TEMPLATES, None)
    return environment.get_template("status.html").render(status=status, **context)


def _parse(status=STATUS, **context):
    return mf2py.parse(doc=f"<div class=\"h-feed\">{_render(status, **context)}</div>")


@pytest.fixture
def entry():
    return _parse()["items"][0]["children"][0]


def test_status_is_an_h_entry(entry):
    assert "h-entry" in entry["type"]


def test_status_is_a_note_and_carries_no_name(entry):
    assert entry["properties"].get("name") is None


def test_status_exposes_its_permalink_as_url(entry):
    assert entry["properties"]["url"] == ["https://example.com/@alice/1"]


def test_status_exposes_the_activity_uri_as_uid(entry):
    assert entry["properties"]["uid"] == ["https://example.com/actors/alice/notes/1"]


def test_status_publishes_its_creation_time(entry):
    assert entry["properties"]["published"] == ["2026-01-01T10:00:00Z"]


def test_status_keeps_the_content_as_e_content(entry):
    assert "Hallo Welt" in entry["properties"]["content"][0]["html"]


def test_hashtags_become_categories(entry):
    assert entry["properties"]["category"] == ["python", "fediverse"]


def test_categories_omit_the_leading_hash(entry):
    assert all(not c.startswith("#") for c in entry["properties"]["category"])


def test_hashtag_links_carry_rel_tag():
    assert _parse()["rels"]["tag"] == ["https://example.com/tags/python",
                                       "https://example.com/tags/fediverse"]


def test_a_status_without_tags_has_no_categories():
    entry = _parse({**STATUS, "tags": []})["items"][0]["children"][0]

    assert entry["properties"].get("category") is None


def test_the_author_is_an_h_card(entry):
    assert "h-card" in entry["properties"]["author"][0]["type"]


def test_the_author_card_exposes_its_url(entry):
    assert entry["properties"]["author"][0]["properties"]["url"] == ["https://example.com/@alice"]


def test_the_author_link_carries_rel_author():
    assert _parse()["rels"]["author"] == ["https://example.com/@alice"]


def test_a_hidden_author_leaves_no_author_property():
    entry = _parse(show_author=False)["items"][0]["children"][0]

    assert entry["properties"].get("author") is None


def test_the_hashtag_name_is_escaped():
    status = {**STATUS, "tags": [{"name": "<script>", "url": "https://example.com/tags/x"}]}

    assert "<script>" not in _render(status)


def test_the_author_avatar_is_marked_as_u_photo():
    status = {**STATUS, "account": {**STATUS["account"], "avatar": "https://example.com/a.png"}}
    entry = _parse(status)["items"][0]["children"][0]

    photo = entry["properties"]["author"][0]["properties"]["photo"][0]

    assert photo["value"] == "https://example.com/a.png"


def test_a_missing_avatar_leaves_no_photo(entry):
    assert entry["properties"]["author"][0]["properties"].get("photo") is None


def test_the_author_name_falls_back_to_the_username():
    status = {**STATUS, "account": {**STATUS["account"], "display_name": ""}}
    entry = _parse(status)["items"][0]["children"][0]

    assert entry["properties"]["author"][0]["properties"]["name"] == ["alice"]

