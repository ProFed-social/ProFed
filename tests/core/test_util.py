# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.util import extract_component_names


def test_extract_component_names_passes_list_through():
    assert extract_component_names(["api", "user_activities"]) == ["api", "user_activities"]


def test_extract_component_names_splits_string():
    assert extract_component_names("api user_activities") == ["api", "user_activities"]


def test_extract_component_names_empty_string():
    assert extract_component_names("") == []


def test_extract_component_names_splits_on_arbitrary_whitespace():
    assert (extract_component_names("api   user_activities\tfollow_handler") ==
            ["api", "user_activities", "follow_handler"])

