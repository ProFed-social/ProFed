# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from profed.components.client import config
from profed.core.config.component_parser import ConfigError


def test_parse_fills_defaults_for_an_empty_section():
    parsed = config.parse({})

    assert parsed["client_id"] == ""
    assert parsed["client_secret"] == ""
    assert parsed["scope"] == "read write"
    assert parsed["session_ttl"] == 86400
    assert parsed["cookie_secure"] is True
    assert parsed["quick_reactions"] == ["👍", "❤️", "👏", "💡", "😂"]


def test_parse_keeps_configured_values_and_coerces_types():
    parsed = config.parse({"client_id": "cid",
                           "client_secret": "sec",
                           "scope": "read",
                           "session_ttl": "3600",
                           "cookie_secure": "false"})

    assert parsed["client_id"] == "cid"
    assert parsed["client_secret"] == "sec"
    assert parsed["scope"] == "read"
    assert parsed["session_ttl"] == 3600
    assert parsed["cookie_secure"] is False


def test_parse_preserves_unrelated_keys():
    parsed = config.parse({"theme_dir": "/themes/foo", "force_external": "true"})

    assert parsed["theme_dir"] == "/themes/foo"
    assert parsed["force_external"] == "true"
    assert parsed["client_id"] == ""


def test_quick_reactions_take_names_code_points_and_emoji():
    parsed = config.parse({"quick_reaction_1": "waving hand: medium-dark skin tone",
                           "quick_reaction_3": "\\u1F468 \\u1F3FD \\u200D \\u1F9B2",
                           "quick_reaction_5": "🎉"})

    assert parsed["quick_reactions"] == ["👋", "❤️", "👨\u200d🦲", "💡", "🎉"]


def test_a_blank_quick_reaction_keeps_its_default():
    assert config.parse({"quick_reaction_2": "   "})["quick_reactions"][1] == "❤️"


def test_an_unknown_quick_reaction_is_a_configuration_error():
    with pytest.raises(ConfigError):
        config.parse({"quick_reaction_2": "thumbs upp"})

