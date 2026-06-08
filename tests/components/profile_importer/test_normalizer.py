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

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["avatar"] == "https://example.com/photo.jpg"


def test_normalize_extracts_header_from_u_featured():
    mf2 = _mf2({"name": ["Alice"], "featured": ["https://example.com/banner.jpg"]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["header"] == "https://example.com/banner.jpg"


def test_normalize_extracts_header_from_u_x_header():
    mf2 = _mf2({"name": ["Alice"], "x-header": ["https://example.com/header.jpg"]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["header"] == "https://example.com/header.jpg"


def test_normalize_u_featured_takes_precedence_over_u_x_header():
    mf2 = _mf2({"name": ["Alice"],
                "featured": ["https://example.com/featured.jpg"],
                "x-header": ["https://example.com/header.jpg"]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["header"] == "https://example.com/featured.jpg"


def test_normalize_leaves_image_fields_none_when_no_photo():
    mf2 = _mf2({"name": ["Alice"]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["avatar"] is None
    assert sources["header"] is None


def _mf2_with_hcard(hcard_props, resume_props=None):
    props = resume_props or {"name": ["Alice"]}
    props["contact"] = [{"type": ["h-card"], "properties": hcard_props}]
    return {"items": [{"type": ["h-resume"], "properties": props}]}


def test_normalize_extracts_avatar_from_hcard_photo():
    mf2    = _mf2_with_hcard({"photo": [{"value": "https://example.com/photo.jpg",
                                         "alt": "Profile photo"}]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["avatar"] == "https://example.com/photo.jpg"


def test_normalize_extracts_header_from_hcard_featured():
    mf2    = _mf2_with_hcard({"featured": [{"value": "https://example.com/banner.jpg",
                                            "alt": "Header"}]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["header"] == "https://example.com/banner.jpg"


def test_normalize_extracts_header_from_hcard_x_header():
    mf2    = _mf2_with_hcard({"x-header": [{"value": "https://example.com/header.jpg",
                                            "alt": "Header"}]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["header"] == "https://example.com/header.jpg"


def test_normalize_hresume_photo_takes_precedence_over_hcard_photo():
    mf2    = _mf2_with_hcard({"photo": [{"value": "https://example.com/hcard.jpg"}]},
                              resume_props={"name": ["Alice"],
                                            "photo": ["https://example.com/resume.jpg"]})

    _, sources = normalize_mf2_to_profile(mf2, "alice")

    assert sources["avatar"] == "https://example.com/resume.jpg"


def test_normalize_uses_contact_name_when_resume_has_no_name():
    mf2 = _mf2_with_hcard({"name": ["Christof Josef Donat"]},
                          resume_props={"summary": []})
    profile, _ = normalize_mf2_to_profile(mf2, "christof")
    assert profile.name == "Christof Josef Donat"


def test_normalize_experience_reads_organization_from_location():
    mf2 = _mf2({"name": ["Alice"],
                "experience": [{"type": ["h-event"],
                                "properties": {"name": ["Senior Engineer"],
                                               "location": ["Acme Corp"],
                                               "start": ["2020-01"],
                                               "end": ["2021-01"]}}]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    job = profile.resume.experience[0]
    assert job["name"] == "Senior Engineer"
    assert job["organization"] == "Acme Corp"


def test_normalize_reads_projects_from_x_project():
    mf2 = _mf2({"name": ["Alice"],
                "x-project": [{"type": ["h-entry"],
                               "properties": {"name": ["Project ProFed"]}}]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.resume.projects[0]["name"] == "Project ProFed"


def test_normalize_summary_falls_back_to_hcard_note():
    mf2 = _mf2_with_hcard({"note": ["over 30 years of experience"]},
                          resume_props={"experience": []})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.summary == "over 30 years of experience"


def test_normalize_links_experience_to_projects_by_id():
    mf2 = _mf2({"name": ["Alice"],
                "experience": [{"type": ["h-event"],
                                "properties": {"name": ["Engineer"],
                                               "x-project": ["https://x.test/cv/#proj-a",
                                                             "https://x.test/cv/#proj-b"]}}],
                "x-project": [{"type": ["h-entry"], "id": "proj-a",
                               "properties": {"name": ["Project A"]}},
                              {"type": ["h-entry"], "id": "proj-b",
                               "properties": {"name": ["Project B"]}}]})

    profile, _ = normalize_mf2_to_profile(mf2, "alice")

    assert profile.resume.experience[0]["projects"] == ["Project A", "Project B"]

