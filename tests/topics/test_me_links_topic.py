# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.me_links_topic import (link_id,
                                          link_parts,
                                          validate_me_links_event,
                                          validate_me_links_snapshot_item)


CHECKED = {"profile_url": "https://p.test/@alice",
           "checked_at": "2026-08-30T10:00:00+00:00",
           "stable_since": "2026-08-29T10:00:00+00:00"}


def test_a_verified_event_passes():
    assert validate_me_links_event("verified", CHECKED) == dict(CHECKED,
                                                                last_modified=None,
                                                                etag=None,
                                                                content_hash=None)


def test_an_unverified_event_passes():
    assert validate_me_links_event("unverified", CHECKED) is not None


def test_a_gone_event_passes():
    assert validate_me_links_event("gone", CHECKED) is not None


def test_an_unknown_verb_is_rejected():
    assert validate_me_links_event("bogus", CHECKED) is None


def test_a_check_without_a_time_is_rejected():
    assert validate_me_links_event("verified", {}) is None


def test_a_check_without_a_stability_is_rejected():
    assert validate_me_links_event("verified", {"checked_at": "2026-08-30T10:00:00+00:00"}) is None


def test_a_check_without_a_stability_is_rejected():
    incomplete = {"profile_url": "https://p.test/@alice", "checked_at": "2026-08-30T10:00:00+00:00"}

    assert validate_me_links_event("verified", incomplete) is None


def test_the_freshness_headers_are_kept():
    payload = dict(CHECKED, last_modified="Sat, 30 Aug 2026 08:00:00 GMT", etag='"abc"', content_hash="deadbeef")

    validated = validate_me_links_event("verified", payload)

    assert validated["last_modified"] == "Sat, 30 Aug 2026 08:00:00 GMT"
    assert validated["etag"] == '"abc"'
    assert validated["content_hash"] == "deadbeef"


def test_a_deleted_event_needs_no_payload():
    assert validate_me_links_event("deleted", {}) == {}


def test_a_tick_is_not_an_event():
    assert validate_me_links_event("Tick", {}) is None


def test_a_snapshot_item_is_validated_like_a_check():
    assert validate_me_links_snapshot_item(CHECKED) is not None


def test_a_snapshot_item_without_a_time_is_rejected():
    assert validate_me_links_snapshot_item({}) is None


def test_the_link_id_joins_both_urls():
    assert link_id("https://a.test/users/alice", "https://b.test/x") == "https://a.test/users/alice|https://b.test/x"


def test_the_link_id_can_be_taken_apart_again():
    parts = link_parts(link_id("https://a.test/@alice", "https://b.test/x"))

    assert parts == ["https://a.test/@alice", "https://b.test/x"]


def test_a_link_with_a_pipe_stays_intact():
    parts = link_parts(link_id("https://a.test/@alice", "https://b.test/x|y"))

    assert parts == ["https://a.test/@alice", "https://b.test/x|y"]

