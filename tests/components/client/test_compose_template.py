# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

from profed.components.client.templating import STANDARD_TEMPLATES, build_environment


_ENV = build_environment(STANDARD_TEMPLATES, None)


def _page(**context):
    return _ENV.get_template("home.html").render(blocks=[], **context)


def _editor(**context):
    return _ENV.get_template("compose.html").render(**context)


def _chat(**context):
    return _ENV.get_template("conversation.html").render(active_id="42", messages=[], following=None, **context)


def test_a_logged_in_visitor_gets_a_button_to_start_a_post():
    assert "compose-open" in _page(current_username="alice")


def test_a_logged_in_visitor_gets_the_editor_as_a_dialog():
    assert "<dialog" in _page(current_username="alice")


def test_an_anonymous_visitor_gets_no_editor():
    page = _page()

    assert "compose-open" not in page
    assert "compose-dialog" not in page


def test_the_timeline_no_longer_carries_the_editor_above_the_posts():
    page = _page(current_username="alice")

    assert page.index("h-feed posts") < page.index("compose-dialog")


def test_the_editor_can_cancel_without_posting():
    assert "compose-close" in _editor()


def test_the_editor_sends_its_files_as_multipart():
    editor = _editor()

    assert 'hx-encoding="multipart/form-data"' in editor
    assert 'enctype="multipart/form-data"' in editor


def test_several_attachments_can_be_chosen_at_once():
    picker = re.search(r'<input class="compose-files"[^>]*>', _editor(), re.DOTALL)[0]

    assert "multiple" in picker
    assert 'name="media"' in picker


def test_the_file_dialog_offers_every_kind_we_accept():
    picker = re.search(r'<input class="compose-files"[^>]*>', _editor(), re.DOTALL)[0]
    accepted = re.search(r'accept="([^"]+)"', picker)[1]

    assert set(accepted.split(",")) == {"image/*", "video/*", "audio/*", "application/pdf"}


def test_every_visibility_can_be_chosen():
    chooser = re.search(r'<select class="compose-visibility".*?</select>', _editor(), re.DOTALL)[0]

    assert re.findall(r'<option value="([^"]+)"', chooser) == ["public", "unlisted", "private", "direct"]


def test_a_content_warning_stays_out_of_the_way_until_it_is_wanted():
    warning = re.search(r'<input class="compose-warning"[^>]*>', _editor())[0]

    assert 'name="spoiler_text"' in warning
    assert "hidden" in warning


def test_the_language_can_be_picked_from_the_ones_we_support():
    editor = _editor()
    field = re.search(r'<input class="compose-language"[^>]*>', editor, re.DOTALL)[0]

    assert 'list="compose-languages"' in field
    assert '<option value="de">' in editor
    assert '<option value="ast">' in editor


def test_the_language_the_author_usually_writes_in_is_filled_in():
    editor = _editor(posting={"visibility": "public", "language": "de"})

    assert 'value="de"' in re.search(r'<input class="compose-language"[^>]*>', editor, re.DOTALL)[0]


def test_the_visibility_the_author_usually_posts_with_is_preselected():
    chooser = re.search(r'<select class="compose-visibility".*?</select>',
                        _editor(posting={"visibility": "private", "language": ""}), re.DOTALL)[0]

    assert '<option value="private" selected>' in chooser


def test_the_editor_renders_even_without_posting_defaults():
    chooser = re.search(r'<select class="compose-visibility".*?</select>', _editor(), re.DOTALL)[0]

    assert '<option value="public" selected>' in chooser


def test_the_editor_sits_in_the_layout_so_every_page_has_it():
    assert "compose-dialog" in _ENV.get_template("base.html").render(current_username="alice")


def test_the_chat_editor_offers_to_unfold_itself():
    chat = _chat()

    assert "conversation-expand" in chat
    assert 'aria-expanded="false"' in chat


def test_the_unfolded_chat_editor_is_hidden_until_it_is_wanted():
    extras = re.search(r'<div class="conversation-extras"[^>]*>', _chat())[0]

    assert "hidden" in extras


def test_the_chat_editor_offers_images_with_alt_texts():
    chat = _chat()

    assert 'name="media"' in chat
    assert "compose-previews" in chat
    assert "compose-attach" in chat


def test_the_chat_editor_offers_a_warning_and_a_language():
    chat = _chat()

    assert 'name="spoiler_text"' in chat
    assert 'name="language"' in chat


def test_the_chat_editor_does_not_let_anyone_change_the_visibility():
    assert "compose-visibility" not in _chat()


def test_the_chat_editor_sends_its_files_as_multipart():
    chat = _chat()

    assert 'hx-encoding="multipart/form-data"' in chat
    assert 'enctype="multipart/form-data"' in chat


def test_both_editors_share_the_one_list_of_languages():
    assert _editor().count('<datalist id="compose-languages"') == 1
    assert '<datalist id="compose-languages"' not in _chat()


def test_both_editors_are_bound_by_the_same_script():
    assert "data-editor" in _editor()
    assert "data-editor" in _chat()

