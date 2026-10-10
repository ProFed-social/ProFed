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


def _video(name, description=None, preview=None, width=1920, height=1080):
    return {"type": "video",
            "mime_type": "video/mp4",
            "url": f"https://remote.example/{name}.mp4",
            "preview_url": preview,
            "description": description,
            "meta": {"original": {"width": width, "height": height}} if width else {}}


def _audio(name, description=None):
    return {"type": "audio",
            "mime_type": "audio/mpeg",
            "url": f"https://remote.example/{name}.mp3",
            "preview_url": None,
            "description": description,
            "meta": {}}


def _pdf(name, description=None, filename=None, width=794, height=1123):
    return {"type": "unknown",
            "mime_type": "application/pdf",
            "url": f"https://remote.example/{name}.pdf",
            "preview_url": None,
            "filename": filename,
            "description": description,
            "meta": {"original": {"width": width, "height": height}} if width else {}}


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
    assert 'data-media-open="https://remote.example/a.jpg"' in html


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


def test_each_image_carries_its_aspect_ratio_for_the_layout():
    html = _render([_image("a")])

    assert "--ratio: 1.3333" in html


def test_a_full_row_is_marked_so_it_may_grow():
    html = _render([_image(name) for name in "abc"])

    assert 'class="media-row fills"' in html
    assert len(re.findall(r"media-item", html)) == 3


def test_a_timeline_entry_shows_at_most_three_rows():
    html = _render([_image(f"img{number}") for number in range(10)])

    assert len(re.findall(r'class="media-row', html)) == 3
    assert len(re.findall(r"media-item", html)) == 9
    assert "+1" in html


def test_the_grid_reports_the_total_so_the_client_can_count_for_itself():
    html = _render([_image(f"img{number}") for number in range(10)])

    assert 'data-media-total="10"' in html


def test_the_grid_reports_the_row_limit_so_the_client_can_enforce_it():
    assert 'data-media-budget="3"' in _render([_image("a")])


def test_a_lifted_row_limit_leaves_the_client_unbounded():
    assert "data-media-budget" not in _render([_image("a")], media_rows_limit=None)


def test_the_row_limit_can_be_lifted():
    html = _render([_image(f"img{number}") for number in range(10)], media_rows_limit=None)

    assert len(re.findall(r"media-item", html)) == 10
    assert "media-more" not in html


def test_a_video_shows_its_poster_and_opens_in_the_viewer():
    html = _render([_video("v", preview="https://remote.example/v-poster.jpg")])

    assert 'src="https://remote.example/v-poster.jpg"' in html
    assert 'data-media-open="https://remote.example/v.mp4"' in html
    assert 'data-media-kind="video"' in html


def test_a_video_in_the_grid_does_not_decode_itself_before_it_is_asked_to():
    assert "<video" not in _render([_video("v")])


def test_a_video_never_starts_on_its_own():
    assert "autoplay" not in _render([_video("v")])


def test_a_video_sits_in_the_grid_next_to_the_images():
    html = _render([_image("a"), _video("v")])

    assert "media-grid" in html
    assert len(re.findall(r"media-item", html)) == 2


def test_an_audio_attachment_gets_a_player_of_its_own_outside_the_grid():
    html = _render([_audio("s")])

    assert '<audio src="https://remote.example/s.mp3"' in html
    assert "media-grid" not in html


def test_an_audio_attachment_breaks_the_grid_in_two():
    html = _render([_image("a"), _audio("s"), _image("b")])

    assert len(re.findall(r'class="media-grid"', html)) == 2
    assert html.index("media-grid") < html.index("<audio") < html.rindex("media-grid")


def test_the_description_of_an_audio_attachment_is_shown_because_there_is_nothing_to_look_at():
    assert "Ein Interview" in _render([_audio("s", description="Ein Interview")])


def test_a_document_opens_in_the_viewer_rather_than_a_new_tab():
    html = _render([_pdf("d")])

    assert 'data-media-open="https://remote.example/d.pdf"' in html
    assert 'data-media-kind="document"' in html
    assert 'href="https://remote.example/d.pdf"' not in html


def test_a_document_is_tiled_as_a_square_whatever_its_pages_measure():
    assert "--ratio: 1.0000" in _render([_pdf("d")])


def test_a_document_shows_an_icon_and_its_filename():
    html = _render([_pdf("d", filename="Jahresbericht.pdf")])

    assert "media-document-icon" in html
    assert "Jahresbericht.pdf" in html


def test_a_document_without_a_filename_falls_back_to_its_description():
    assert "Quartalszahlen" in _render([_pdf("d", description="Quartalszahlen")])


def test_an_image_opens_unscaled_in_the_same_viewer():
    html = _render([_image("a", preview="https://remote.example/a-small.jpg")])

    assert 'data-media-open="https://remote.example/a.jpg"' in html
    assert 'data-media-kind="image"' in html


def test_every_page_carries_one_viewer_for_all_three_kinds():
    environment = build_environment(STANDARD_TEMPLATES, None)
    rendered = environment.get_template("base.html").render(current_username="alice")

    assert rendered.count("data-media-viewer") == 2
    assert "media-viewer-image" in rendered
    assert "media-viewer-video" in rendered
    assert "media-viewer-frame" in rendered


def test_the_home_timeline_shows_images_too():
    part = dict(_status([_image("a")]), id="1", created_at="2026-01-01T10:00:00.000Z")
    block = {"parts": [part], "booster": None, "boosted": [], "cursor": "1"}
    environment = build_environment(STANDARD_TEMPLATES, None)

    assert "media-grid" in environment.get_template("block.html").module.timeline_block(block)


def test_a_chat_message_shows_images_too():
    message = dict(_status([_image("a")]), id="1")
    environment = build_environment(STANDARD_TEMPLATES, None)
    rendered = environment.get_template("conversation_messages_page.html").render(messages=[message], conversation_id="1")

    assert "media-grid" in rendered

