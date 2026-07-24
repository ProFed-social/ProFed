# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import mf2py
import pytest
from profed.components.client.templating import STANDARD_TEMPLATES, build_environment
from profed.components.profile_importer.normalizer import normalize_mf2_to_profile


RESUME = {"experience": [{"name": "Entwicklerin",
                          "organization": "ACME",
                          "start": "2020",
                          "end": "2024",
                          "description": "Backend-Arbeit",
                          "url": "https://acme.example",
                          "projects": []}],
          "education": [{"name": "Informatik",
                         "organization": "Uni",
                         "start": "2014",
                         "end": "2018",
                         "description": "Studium"}],
          "projects": [{"name": "ProFed",
                        "description": "Fediverse fuer Berufliches",
                        "url": "https://codeberg.org/ProFed"}],
          "skills": [{"name": "Python"}, {"name": "PostgreSQL"}]}

ACCOUNT = {"username": "alice",
           "acct": "alice",
           "display_name": "Alice Beispiel",
           "url": "https://example.com/@alice",
           "note": "<p>Entwicklerin</p>",
           "avatar": "",
           "header": "",
           "created_at": "2026-01-01T00:00:00.000Z",
           "followers_count": 1,
           "following_count": 2,
           "statuses_count": 3,
           "fields": [],
           "resume": RESUME}


def _parse(account):
    environment = build_environment(STANDARD_TEMPLATES, None)
    html = environment.get_template("profile.html").render(account=account,
                                                           statuses=[],
                                                           handle="alice",
                                                           relationship=None)
    return mf2py.parse(doc=html)


def _import(account=ACCOUNT):
    return normalize_mf2_to_profile(_parse(account), username_template="{name}")[0]


@pytest.fixture
def imported():
    return _import()


def test_a_profile_with_a_resume_yields_a_top_level_h_resume():
    assert any("h-resume" in item["type"] for item in _parse(ACCOUNT)["items"])


def test_the_card_becomes_the_contact_of_the_resume():
    resume = next(i for i in _parse(ACCOUNT)["items"] if "h-resume" in i["type"])

    assert [c["type"] for c in resume["properties"]["contact"]] == [["h-card"]]


def test_a_profile_without_a_resume_keeps_the_card_at_the_top_level():
    items = _parse({**ACCOUNT, "resume": None})["items"]

    assert any("h-card" in item["type"] for item in items)


def test_the_own_page_can_be_imported(imported):
    assert imported is not None


def test_the_name_survives_the_roundtrip(imported):
    assert imported.name == "Alice Beispiel"


def test_the_experience_survives_the_roundtrip(imported):
    assert imported.resume.experience[0]["name"] == "Entwicklerin"


def test_the_employer_survives_the_roundtrip(imported):
    assert imported.resume.experience[0]["organization"] == "ACME"


def test_the_experience_period_survives_the_roundtrip(imported):
    entry = imported.resume.experience[0]

    assert (entry["start"], entry["end"]) == ("2020", "2024")


def test_the_experience_description_survives_the_roundtrip(imported):
    assert imported.resume.experience[0]["description"] == "Backend-Arbeit"


def test_the_education_survives_the_roundtrip(imported):
    assert imported.resume.education[0]["name"] == "Informatik"


def test_the_education_period_survives_the_roundtrip(imported):
    entry = imported.resume.education[0]

    assert (entry["start"], entry["end"]) == ("2014", "2018")


def test_projects_are_not_imported_as_experience(imported):
    assert [entry["name"] for entry in imported.resume.experience] == ["Entwicklerin"]


def test_the_projects_survive_the_roundtrip(imported):
    assert imported.resume.projects[0]["name"] == "ProFed"


def test_the_project_description_survives_the_roundtrip(imported):
    assert imported.resume.projects[0]["description"] == "Fediverse fuer Berufliches"


def test_the_skills_survive_the_roundtrip(imported):
    assert [skill["name"] for skill in imported.resume.skills] == ["Python", "PostgreSQL"]

