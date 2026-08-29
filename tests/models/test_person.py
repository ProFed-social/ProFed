# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models import UserProfile
from profed.models.activity_pub import Person


def test_fields_become_property_value_attachments():
    profile = UserProfile(username="alice",
                          fields=[{"name": "GitHub", "value": "https://github.com/alice"}])

    assert Person.from_user(profile).attachment == [{"type": "PropertyValue",
                                                     "name": "GitHub",
                                                     "value": "https://github.com/alice"}]


def test_every_field_becomes_its_own_attachment():
    profile = UserProfile(username="alice",
                          fields=[{"name": "GitHub", "value": "https://github.com/alice"},
                                  {"name": "Site", "value": "https://alice.test/"}])

    assert [entry["name"] for entry in Person.from_user(profile).attachment] == ["GitHub", "Site"]


def test_a_profile_without_fields_has_no_attachment():
    assert Person.from_user(UserProfile(username="alice")).attachment is None


def test_an_incomplete_field_is_dropped():
    profile = UserProfile(username="alice",
                          fields=[{"name": "GitHub"}, {"value": "https://a.test/x"}])

    assert Person.from_user(profile).attachment is None

