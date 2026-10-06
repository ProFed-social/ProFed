# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

import pytest

from profed.components.client.templating import STANDARD_TEMPLATES, build_environment


def _image(name, description=None, preview=None):
    return {"type": "image",
            "url": f"https://remote.example/{name}.jpg",
            "preview_url": preview,
            "description": description,
            "meta": {"original": {"width": 800, "height": 600}}}


def _status(attachments):
    return {"id": "1",
            "visibility": "public",
            "content": "<p>Hallo Welt</p>",
            "created_at": "2026-01-01T10:00:00.000Z",
            "url": "https://example.com/@alice/1",
            "uri": "https://example.com/actors/alice/notes/1",
            "tags": [],
            "media_attachments": attachments,
            "account": {"url": "https://example.com/@alice",
                        "acct": "alice",
                        "display_name": "Alice",
                        "username": "alice",
                        "avatar": ""}}


@pytest.fixture(autouse=True)
def a_domain(monkeypatch):
    monkeypatch.setattr("profed.components.client.templating.domain", lambda: "example.com")


def _render(attachments, **context):
    environment = build_environment(STANDARD_TEMPLATES, None)
    return environment.get_template("status.html").render(status=_status(attachments), **context)


def test_a_post_without_images_has_no_media_grid():
    assert "media-grid" not in _render([])


def test_an_image_is_rendered_with_its_source():
    assert 'src="https://remote.example/a.jpg"' in _render([_image("a")])


def test_the_preview_is_used_when_there_is_one():
    html = _render([_image("a", preview="https://remote.example/a-small.jpg")])

    assert 'src="https://remote.example/a-small.jpg"' in html
    assert 'href="https://remote.example/a.jpg"' in html

def test_the_description_becomes_the_alt_text():
    assert 'alt="Ein Diagramm"' in _render([_image("a", description="Ein Diagramm")])


def test_the_description_is_not_repeated_as_visible_text():
    html = _render([_image("a", description="Ein sehr langer beschreibender Text")])

    assert html.count("Ein sehr langer beschreibender Text") == 1
    assert "figcaption" not in html


def test_an_image_without_a_description_still_carries_an_empty_alt():
    assert 'alt=""' in _render([_image("a")])


def test_the_dimensions_are_set_so_the_layout_does_not_jump():
    html = _render([_image("a")])

    assert 'width="800"' in html
    assert 'height="600"' in html


def test_images_are_loaded_lazily():
    assert 'loading="lazy"' in _render([_image("a")])


def test_three_images_put_the_first_one_on_its_own_row():
    html = _render([_image(name) for name in "abc"])

    assert len(re.findall(r'class="media-row single"', html)) == 1
    assert len(re.findall(r"media-item", html)) == 3


def test_a_timeline_entry_shows_at_most_three_rows():
    html = _render([_image(f"img{number}") for number in range(10)])

    assert len(re.findall(r"media-item", html)) == 6
    assert "+4" in html


def test_the_row_limit_can_be_lifted():
    html = _render([_image(f"img{number}") for number in range(10)], media_rows_limit=None)

    assert len(re.findall(r"media-item", html)) == 10
    assert "media-more" not in html

