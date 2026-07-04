# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.sanitize import sanitize_html, strip_tags, sanitize_document


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


def test_keeps_small_tag():
    assert sanitize_html("<p>x <small>y</small></p>") == "<p>x <small>y</small></p>"


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


def test_strip_tags_removes_all_tags():
    assert strip_tags("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_tags_unescapes_and_strips_nested_encoding():
    assert strip_tags("a &lt;script&gt;alert(1)&lt;/script&gt; b") == "a  b"


def test_strip_tags_preserves_pem():
    pem = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0B==\n-----END PUBLIC KEY-----\n'
    assert strip_tags(pem) == pem


def test_strip_tags_passes_through_empty_and_none():
    assert strip_tags("") == ""
    assert strip_tags(None) is None


def test_sanitize_document_sanitizes_html_field():
    out = sanitize_document({"summary": "<p>hi</p><script>x</script>"})

    assert out["summary"] == "<p>hi</p>"


def test_sanitize_document_strips_text_field():
    out = sanitize_document({"name": "Bob <b>Evil</b>"})

    assert out["name"] == "Bob Evil"


def test_sanitize_document_handles_language_map():
    out = sanitize_document({"summaryMap": {"en": "<p>hi</p><script>x</script>",
                                            "de": "<p>hallo</p>"}})

    assert out["summaryMap"] == {"en": "<p>hi</p>", "de": "<p>hallo</p>"}


def test_sanitize_document_html_field_as_dict_is_language_mapped():
    out = sanitize_document({"content": {"en": "<p>ok</p><script>y</script>"}})

    assert out["content"] == {"en": "<p>ok</p>"}


def test_sanitize_document_scopes_description_to_resume_subtree():
    out = sanitize_document({"resume": {"experience": [{"description":
                                                        "<p>ok</p><script>b</script>"}]}})

    assert out["resume"]["experience"][0]["description"] == "<p>ok</p>"


def test_sanitize_document_description_outside_resume_is_stripped():
    out = sanitize_document({"description": "<p>ok</p><script>b</script>"})

    assert out["description"] == "ok"


def test_sanitize_document_preserves_pem():
    pem = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0B==\n-----END PUBLIC KEY-----\n'
    out = sanitize_document({"publicKey": {"publicKeyPem": pem}})

    assert out["publicKey"]["publicKeyPem"] == pem


def test_sanitize_document_passes_through_non_strings():
    out = sanitize_document({"n": 42, "b": True, "x": None})

    assert out == {"n": 42, "b": True, "x": None}


def test_strip_tags_drops_javascript_scheme():
    assert strip_tags("javascript:alert(1)") == ""


def test_strip_tags_drops_data_scheme():
    assert strip_tags("data:text/html,<b>x</b>") == ""


def test_strip_tags_drops_obfuscated_script_scheme():
    assert strip_tags("java\tscript:alert(1)") == ""


def test_strip_tags_drops_typescript_like_scheme():
    assert strip_tags("typescript:whatever") == ""


def test_strip_tags_drops_scheme_revealed_after_tag_strip():
    assert strip_tags("<b>javascript:alert(1)</b>") == ""


def test_strip_tags_keeps_https_url():
    assert strip_tags("https://example.com/a") == "https://example.com/a"


def test_strip_tags_keeps_acct_scheme():
    assert strip_tags("acct:bob@example.com") == "acct:bob@example.com"


def test_strip_tags_keeps_text_with_colon():
    assert strip_tags("Re:Zero is great") == "Re:Zero is great"


def test_strip_tags_keeps_scheme_not_at_start():
    assert strip_tags("see javascript:alert(1)") == "see javascript:alert(1)"


def test_strip_tags_logs_on_dangerous_scheme(caplog):
    with caplog.at_level("WARNING"):
        strip_tags("javascript:alert(1)")

    assert "disallowed URL scheme" in caplog.text


def test_sanitize_document_drops_dangerous_url_in_field():
    out = sanitize_document({"icon": {"url": "data:text/html,x"}, "inbox": "https://x/in"})

    assert out["icon"]["url"] == ""
    assert out["inbox"] == "https://x/in"

