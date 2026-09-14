# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.known_servers_topic import (host_of,
                                               validate_known_servers_event,
                                               validate_known_servers_snapshot_item)


OBSERVED = {"activity_type": "EmojiReact", "observed_at": "2026-09-13T10:00:00+00:00"}

UPDATED = {"checked_at": "2026-09-13T10:00:00+00:00", "stable_since": "2026-09-01T10:00:00+00:00"}


def test_a_discovered_event_needs_no_payload():
    assert validate_known_servers_event("discovered", {}) == {}


def test_a_lost_event_needs_no_payload():
    assert validate_known_servers_event("lost", {}) == {}


def test_an_observation_passes():
    assert validate_known_servers_event("observed", OBSERVED) == OBSERVED


def test_an_observation_without_a_time_is_rejected():
    assert validate_known_servers_event("observed", {"activity_type": "EmojiReact"}) is None


def test_an_observation_without_an_activity_is_rejected():
    assert validate_known_servers_event("observed", {"observed_at": "2026-09-13T10:00:00+00:00"}) is None


def test_an_update_passes_and_defaults_to_no_features():
    assert validate_known_servers_event("updated", UPDATED) == dict(UPDATED,
                                                                    software=None,
                                                                    features=[],
                                                                    last_modified=None,
                                                                    etag=None,
                                                                    content_hash=None)


def test_an_update_keeps_software_and_features():
    validated = validate_known_servers_event("updated", dict(UPDATED,
                                                             software="pleroma",
                                                             features=["pleroma_emoji_reactions"]))

    assert validated["software"] == "pleroma"
    assert validated["features"] == ["pleroma_emoji_reactions"]


def test_an_update_keeps_the_freshness_headers():
    validated = validate_known_servers_event("updated", dict(UPDATED,
                                                             last_modified="Sat, 12 Sep 2026 08:00:00 GMT",
                                                             etag='"abc"',
                                                             content_hash="deadbeef"))

    assert validated["last_modified"] == "Sat, 12 Sep 2026 08:00:00 GMT"
    assert validated["etag"] == '"abc"'
    assert validated["content_hash"] == "deadbeef"


def test_an_update_without_a_stability_is_rejected():
    assert validate_known_servers_event("updated", {"checked_at": "2026-09-13T10:00:00+00:00"}) is None


def test_an_unknown_verb_is_rejected():
    assert validate_known_servers_event("bogus", UPDATED) is None


def test_a_tick_is_not_an_event():
    assert validate_known_servers_event("Tick", {}) is None


def test_a_snapshot_item_is_validated_like_an_update():
    assert validate_known_servers_snapshot_item(UPDATED) is not None


def test_a_snapshot_item_without_a_time_is_rejected():
    assert validate_known_servers_snapshot_item({}) is None


def test_the_host_comes_out_of_an_actor_url():
    assert host_of("https://Pleroma.Example/users/bob") == "pleroma.example"


def test_a_bare_host_stays_a_host():
    assert host_of("pleroma.example") == "pleroma.example"


def test_the_default_port_is_dropped():
    assert host_of("https://ex.test:443/x") == "ex.test"
    assert host_of("http://ex.test:80/x") == "ex.test"


def test_any_other_port_is_kept():
    assert host_of("https://ex.test:8443/x") == "ex.test:8443"


def test_credentials_are_dropped():
    assert host_of("https://user:pw@ex.test/x") == "ex.test"


def test_punycode_is_left_as_it_is():
    assert host_of("https://xn--mnchen-3ya.example/users/a") == "xn--mnchen-3ya.example"


def test_an_ipv6_host_keeps_its_brackets():
    assert host_of("http://[2001:db8::1]:8080/x") == "[2001:db8::1]:8080"
    assert host_of("https://[2001:db8::1]/x") == "[2001:db8::1]"


def test_an_impossible_port_gives_no_host():
    assert host_of("https://ex.test:99999/x") == ""


def test_something_that_is_not_a_host_gives_no_host():
    assert host_of("not a url") == ""
    assert host_of("") == ""
    assert host_of("   ") == ""

