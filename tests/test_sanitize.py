# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.sanitize import sanitize_html


def test_strips_script_tag_and_content():
    assert sanitize_html("<p>hi</p><script>alert(1)</script>") == "<p>hi</p>"


def test_strips_style_tag_and_content():
    assert sanitize_html("<p>hi</p><style>* { color: red }</style>") == "<p>hi</p>"


def test_drops_javascript_url():
    assert "javascript:" not in sanitize_html('<a href="javascript:alert(1)">x</a>')


def test_drops_data_url():
    assert "data:" not in sanitize_html('<a href="data:text/html,x">x</a>')


def test_strips_event_handler_attributes():
    assert sanitize_html('<b onclick="alert(1)">ok</b>') == "<b>ok</b>"


def test_removes_disallowed_tags_but_keeps_text():
    out = sanitize_html("<div>kept</div>")
    assert "div" not in out and "kept" in out


def test_keeps_allowed_formatting():
    out = sanitize_html("<p>a <strong>b</strong> <em>c</em></p>"
                        "<ul><li>i</li></ul><blockquote>q</blockquote>")
    for fragment in ("<p>",
                     "<strong>b</strong>",
                     "<em>c</em>",
                     "<ul>",
                     "<li>i</li>",
                     "<blockquote>q</blockquote>"):
        assert fragment in out


def test_keeps_allowed_link_and_adds_rel():
    out = sanitize_html('<a href="https://example.test/x">l</a>')
    assert 'href="https://example.test/x"' in out
    assert 'rel="nofollow noopener noreferrer"' in out


def test_class_filter_keeps_microformats_and_semantic_drops_rest():
    out = sanitize_html('<a class="status__content__spoiler-link mention h-card" '
                        'href="https://x.test">m</a>')
    assert "status__content__spoiler-link" not in out
    assert "mention" in out and "h-card" in out


def test_is_idempotent():
    once = sanitize_html('<p>x <a href="https://x.test" class="mention">@u</a> '
                         "<strong>b</strong> <script>e()</script></p>")
    assert sanitize_html(once) == once


def test_passes_through_empty_and_none():
    assert sanitize_html("") == ""
    assert sanitize_html(None) is None

