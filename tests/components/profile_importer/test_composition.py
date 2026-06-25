# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from profed.components.profile_importer.composition import apply_template


def test_plain_substitution():
    assert apply_template("{a}_{b}", {"a": "x", "b": "y"}) == "x_y"


def test_literal_without_tags_passes_through():
    assert apply_template("christof", {}) == "christof"


def test_missing_property_defaults_to_empty_string():
    assert apply_template("{a}{b}", {"a": "x"}) == "x"


def test_explicit_fallback_used_when_missing():
    assert apply_template("{a|Anon} posted", {}) == "Anon posted"


def test_explicit_fallback_ignored_when_present():
    assert apply_template("{a|Anon}", {"a": "x"}) == "x"


def test_nested_fallback_is_resolved():
    assert apply_template("{a|{b}}", {"b": "y"}) == "y"


def test_nested_fallback_chain():
    assert apply_template("{summary|{note}}", {"note": "from note"}) == "from note"


def test_substituted_value_is_not_rescanned_for_tags():
    assert apply_template("{a}", {"a": "{b}", "b": "NOPE"}) == "{b}"


def test_literal_html_around_tags():
    assert apply_template("{s} <ul>{n}</ul>",
                          {"s": "<p>x</p>", "n": "<li>a</li>"}) == "<p>x</p> <ul><li>a</li></ul>"


def test_unbalanced_tag_raises():
    with pytest.raises(ValueError):
        apply_template("{a", {})


