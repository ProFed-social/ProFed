# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.profile_importer.normalizer import (_to_url,
                                                           _html_field,
                                                           _reference,
                                                           normalize_mf2_to_profile)

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

def test_normalize_sanitizes_summary():
    mf2 = _mf2({"name":    ["Alice"],
                "summary": ["<p>hi</p><script>x()</script>"]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.summary == "<p>hi</p>"


def test_normalize_name_defaults_to_name_property():
    profile, _ = normalize_mf2_to_profile(_mf2({"name": ["Alice Smith"]}), "alice")
    assert profile.name == "Alice Smith"


def test_normalize_name_composes_from_parts_and_collapses_whitespace():
    mf2 = _mf2_with_hcard({"given-name": ["Christof"], "family-name": ["Donat"]},
                          resume_props={"experience": []})
    profile, _ = normalize_mf2_to_profile(mf2, "christof")
    assert profile.name == "Christof Donat"


def test_normalize_username_from_literal_template():
    profile, _ = normalize_mf2_to_profile(_mf2({"name": ["Alice"]}), "alice")
    assert profile.username == "alice"


def test_normalize_username_composes_from_parts():
    mf2 = _mf2_with_hcard({"given-name": ["Christof"], "family-name": ["Donat"]},
                          resume_props={"experience": []})
    profile, _ = normalize_mf2_to_profile(mf2, "{given-name}_{family-name}")
    assert profile.username == "Christof_Donat"


def test_normalize_returns_none_when_username_empty():
    mf2 = _mf2_with_hcard({"given-name": ["Christof"]}, resume_props={"experience": []})
    assert normalize_mf2_to_profile(mf2, "{missing}") is None


def test_normalize_summary_template_override_composes_html():
    mf2 = _mf2({"x-summary": [{"value": "q",  "html": "<strong>q</strong>"}],
                "x-note":    [{"value": "ab", "html": "<li>a</li><li>b</li>"}]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice",
                                          summary_template="{x-summary} <ul>{x-note}</ul>")
    assert profile.summary == "<strong>q</strong> <ul><li>a</li><li>b</li></ul>"


def test_html_field_prefers_html_over_text():
    props = {"x-description": [{"html": "<p>x</p><script>y</script>", "value": "x"}]}
    assert _html_field(props, "description") == "<p>x</p>"


def test_html_field_falls_back_to_text():
    assert _html_field({"description": ["plain text"]}, "description") == "plain text"


def test_html_field_returns_none_when_absent():
    assert _html_field({}, "description") is None


def test_normalize_project_description_is_html():
    mf2 = _mf2({"name": ["Alice"],
                "x-project": [{"type": ["h-entry"],
                               "properties": {"name": ["ProFed"],
                                              "description": [{"value": "a b",
                                                               "html": "<p>a</p><p>b</p>"}]}}]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.resume.projects[0]["description"] == "<p>a</p><p>b</p>"


def test_normalize_experience_description_from_e_x_variant():
    mf2 = _mf2({"name": ["Alice"],
                "experience": [{"type": ["h-event"],
                                "properties": {"name": ["Engineer"],
                                               "description": ["plain"],
                                               "x-description": [{"value": "rich",
                                                                  "html": "<p>rich</p>"}]}}]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.resume.experience[0]["description"] == "<p>rich</p>"


def test_normalize_reads_project_technologies():
    mf2 = _mf2({"name": ["Alice"],
                "x-project": [{"type": ["h-entry"],
                               "properties": {"name": ["ProFed"],
                                              "technology": ["Python", "FastAPI"]}}]})
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.resume.projects[0]["technologies"] == ["Python", "FastAPI"]


def _h_cite(content, author=None):
    return {"type": ["h-cite"],
            "properties": {"author": [{"type": ["h-card"],
                                       "properties": author or {"name": ["John Doe"],
                                                                "job-title": ["Janitor"],
                                                                "org": ["ACME"]}}],
                           "content": content,
                           "url": ["https://x.example/ref"],
                           "x-verification": ["source"]}}


def _mf2_children(children):
    return {"items": [{"type": ["h-resume"],
                       "properties": {"name": ["Alice"]},
                       "children": children}]}


def test_normalize_reads_reference_from_h_cite_child():
    mf2 = _mf2_children([_h_cite([{"value": "t", "lang": "en", "html": "<p>t</p>"}])])
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    ref = profile.resume.references[0]
    assert ref["author"] == {"name": "John Doe", "role": "Janitor", "organization": "ACME"}
    assert ref["url"] == "https://x.example/ref"
    assert ref["verification"] == "source"


def test_normalize_reference_content_is_language_mapped():
    mf2 = _mf2_children([_h_cite([{"value": "d", "lang": "de", "html": "<p>d</p>"},
                                  {"value": "e", "lang": "en", "html": "<p>e</p>"}])])
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.resume.references[0]["content"] == {"de": "<p>d</p>", "en": "<p>e</p>"}


def test_normalize_reference_content_is_sanitised():
    mf2 = _mf2_children([_h_cite([{"value": "x", "lang": "en",
                                   "html": "<p>ok</p><script>bad</script>"}])])
    profile, _ = normalize_mf2_to_profile(mf2, "alice")
    assert profile.resume.references[0]["content"]["en"] == "<p>ok</p>"


def test_reference_ignores_non_dict():
    assert _reference("not a dict") == {}

