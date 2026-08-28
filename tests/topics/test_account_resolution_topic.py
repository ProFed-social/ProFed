# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.topics.account_resolution_topic import (process_id,
                                                    request_id,
                                                    validate_account_resolution_event,
                                                    validate_account_resolution_snapshot_item)


def _payload(**overrides):
    return {"source": "unknown_actors", "sequence_id": 7, "kind": "jrd", "ordinal": 1, **overrides}


@pytest.mark.parametrize("state", ["attempting",
                                   "request_succeeded",
                                   "request_failed",
                                   "request_not_found",
                                   "request_tombstone"])
def test_every_request_state_passes(state):
    assert validate_account_resolution_event(state, _payload()) is not None


@pytest.mark.parametrize("state", ["resolved", "unresolved"])
def test_every_process_state_passes(state):
    assert validate_account_resolution_event(state, {"source": "unknown_actors", "sequence_id": 7}) is not None


def test_a_succeeded_request_carries_its_document():
    payload = _payload(name="alice@a.test", document={"subject": "acct:alice@a.test"})

    assert validate_account_resolution_event("request_succeeded", payload)["document"]["subject"] \
        == "acct:alice@a.test"


def test_a_failed_request_passes_without_a_document():
    assert validate_account_resolution_event("request_failed", _payload(attempt=2))["attempt"] == 2


def test_an_unknown_event_type_is_rejected():
    assert validate_account_resolution_event("discovered", _payload()) is None


def test_a_payload_without_a_source_is_rejected():
    payload = _payload()
    del payload["source"]

    assert validate_account_resolution_event("attempting", payload) is None


def test_a_payload_without_a_sequence_id_is_rejected():
    payload = _payload()
    del payload["sequence_id"]

    assert validate_account_resolution_event("attempting", payload) is None


def test_a_process_state_needs_no_ordinal():
    payload = _payload()
    del payload["ordinal"]

    assert validate_account_resolution_event("resolved", payload) is not None


def test_the_attempt_defaults_to_zero():
    assert validate_account_resolution_event("attempting", _payload())["attempt"] == 0


def test_a_snapshot_item_passes():
    assert validate_account_resolution_snapshot_item(_payload())["source"] == "unknown_actors"


def test_a_snapshot_item_without_a_source_is_rejected():
    payload = _payload()
    del payload["source"]

    assert validate_account_resolution_snapshot_item(payload) is None


def test_the_request_id_is_deterministic():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        == request_id("unknown_actors", 7, "jrd", 1, 1, "attempting")


def test_the_request_id_separates_the_ordinals():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        != request_id("unknown_actors", 7, "jrd", 2, 1, "attempting")


def test_the_request_id_separates_the_attempts():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        != request_id("unknown_actors", 7, "jrd", 1, 2, "attempting")


def test_the_request_id_separates_the_states():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        != request_id("unknown_actors", 7, "jrd", 1, 1, "request_succeeded")


def test_the_request_id_separates_two_runs_for_the_same_name():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        != request_id("unknown_actors", 9, "jrd", 1, 1, "attempting")


def test_the_request_id_separates_the_source_topics():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        != request_id("raw_activities", 7, "jrd", 1, 1, "attempting")


def test_the_process_id_is_deterministic():
    assert process_id("unknown_actors", 7) == process_id("unknown_actors", 7)


def test_the_process_id_separates_the_runs():
    assert process_id("unknown_actors", 7) != process_id("unknown_actors", 9)


def test_the_process_id_separates_the_source_topics():
    assert process_id("unknown_actors", 7) != process_id("raw_activities", 7)


def test_the_request_id_separates_the_kinds():
    assert request_id("unknown_actors", 7, "jrd", 1, 1, "attempting") \
        != request_id("unknown_actors", 7, "actor", 1, 1, "attempting")


def test_the_request_id_does_not_confuse_kind_and_ordinal():
    assert request_id("unknown_actors", 7, "jrd", 11, 1, "attempting") \
        != request_id("unknown_actors", 7, "jrd1", 1, 1, "attempting")

