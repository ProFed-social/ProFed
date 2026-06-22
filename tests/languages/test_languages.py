# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.languages import supported, is_supported


def test_supported_is_non_empty():
    assert len(supported()) > 100


def test_supported_contains_common_languages():
    codes = supported()
    assert "en" in codes
    assert "de" in codes
    assert "fr" in codes


def test_supported_contains_regional_variants():
    codes = supported()
    assert "pt-BR" in codes
    assert "zh-CN" in codes


def test_supported_contains_three_letter_codes():
    assert "ast" in supported()


def test_is_supported_true_for_known_tag():
    assert is_supported("en")


def test_is_supported_false_for_unknown_tag():
    assert not is_supported("xx-NONSENSE")


def test_supported_is_cached():
    assert supported() is supported()

