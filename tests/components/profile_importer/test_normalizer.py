# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.profile_importer.normalizer import _to_url, normalize_mf2_to_profile


def _mf2(props):
    return {"items": [{"type": ["h-resume"], "properties": props}]}


def test_to_url_returns_string_directly():
    assert _to_url("https://example.com/photo.jpg") == "https://example.com/photo.jpg"


def test_to_url_strips_whitespace():
    assert _to_url("  https://example.com/photo.jpg  ") == "https://example.com/photo.jpg"

def test_to_url_returns_none_for_empty_string():
    assert _to_url("") is None


def test_to_url_extracts_value_from_dict():
    assert _to_url({"value": "https://example.com/photo.jpg"}) == "https://example.com/photo.jpg"


def test_to_url_extracts_url_from_dict():
    assert _to_url({"url": "https://example.com/photo.jpg"}) == "https://example.com/photo.jpg"


def test_to_url_returns_none_for_unrecognised_type():
    assert _to_url(42) is None


def test_normalize_extracts_avatar_source_url():
    mf2 = _mf2({"name": ["Alice"], "photo": ["https://example.com/photo.jpg"]})

    result = normalize_mf2_to_profile(mf2, "alice")

    assert result.avatar_source_url == "https://example.com/photo.jpg"


def test_normalize_extracts_header_from_u_featured():
    mf2 = _mf2({"name": ["Alice"], "featured": ["https://example.com/banner.jpg"]})

    result = normalize_mf2_to_profile(mf2, "alice")

    assert result.header_source_url == "https://example.com/banner.jpg"


def test_normalize_extracts_header_from_u_x_header():
    mf2 = _mf2({"name": ["Alice"], "x-header": ["https://example.com/header.jpg"]})

    result = normalize_mf2_to_profile(mf2, "alice")

    assert result.header_source_url == "https://example.com/header.jpg"


def test_normalize_u_featured_takes_precedence_over_u_x_header():
    mf2 = _mf2({"name":     ["Alice"],
                "featured": ["https://example.com/featured.jpg"],
                "x-header": ["https://example.com/header.jpg"]})

    result = normalize_mf2_to_profile(mf2, "alice")

    assert result.header_source_url == "https://example.com/featured.jpg"


def test_normalize_leaves_image_fields_none_when_no_photo():
    mf2 = _mf2({"name": ["Alice"]})

    result = normalize_mf2_to_profile(mf2, "alice")

    assert result.avatar_source_url is None
    assert result.header_source_url is None

