# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.client import config


def test_parse_fills_defaults_for_an_empty_section():
    parsed = config.parse({})

    assert parsed["client_id"] == ""
    assert parsed["client_secret"] == ""
    assert parsed["scope"] == "read write"
    assert parsed["session_ttl"] == 86400
    assert parsed["cookie_secure"] is True


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

