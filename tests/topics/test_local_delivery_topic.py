# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.local_delivery_topic import validate_local_delivery_event


PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://example.com/actors/bob", "object": "https://example.com/actors/alice"}}


def test_a_known_verb_is_accepted():
    assert validate_local_delivery_event("Follow", PAYLOAD) == PAYLOAD


def test_an_unknown_verb_is_refused():
    assert validate_local_delivery_event("Explode", PAYLOAD) is None

