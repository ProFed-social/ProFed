# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from profed.components.account_resolver import decision


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def _row(state="attempting", attempt=1, age=0, first_age=0, kind="jrd", name="alice@a.test", ordinal=1):
    return {"kind": kind,
            "ordinal": ordinal,
            "state": state,
            "attempt": attempt,
            "name": name,
            "first_attempt_at": NOW - timedelta(seconds=first_age),
            "emitted_at": NOW - timedelta(seconds=age)}


def test_an_unknown_request_is_claimed_as_the_first_attempt():
    assert decision.decide(None, NOW, {}) == ("claim", 1)


def test_a_running_attempt_within_the_lease_waits():
    assert decision.decide(_row(age=10), NOW, {}) == ("wait", 1)


def test_a_running_attempt_past_the_lease_is_claimed_again():
    assert decision.decide(_row(age=121), NOW, {}) == ("claim", 2)


def test_the_lease_is_configurable():
    assert decision.decide(_row(age=11), NOW, {"lease": 10}) == ("claim", 2)


def test_a_failed_request_within_the_backoff_waits():
    assert decision.decide(_row(state="request_failed", age=10), NOW, {}) == ("wait", 1)


def test_a_failed_request_past_the_backoff_is_claimed_again():
    assert decision.decide(_row(state="request_failed", age=301), NOW, {}) == ("claim", 2)


def test_the_backoff_grows_with_the_attempt():
    assert decision.decide(_row(state="request_failed", attempt=2, age=301), NOW, {}) == ("wait", 2)
    assert decision.decide(_row(state="request_failed", attempt=2, age=601), NOW, {}) == ("claim", 3)


def test_a_request_beyond_the_total_time_gives_up():
    assert decision.decide(_row(state="request_failed", first_age=172801, age=100000), NOW, {}) == ("give_up", 1)


def test_the_total_time_is_configurable():
    row = _row(state="request_failed", first_age=11, age=1000)

    assert decision.decide(row, NOW, {"max_total": 10}) == ("give_up", 1)


def test_a_succeeded_request_is_done():
    assert decision.decide(_row(state="request_succeeded"), NOW, {}) == ("done", 1)


def test_a_not_found_request_is_done():
    assert decision.decide(_row(state="request_not_found"), NOW, {}) == ("done", 1)


def test_a_tombstone_request_is_done():
    assert decision.decide(_row(state="request_tombstone"), NOW, {}) == ("done", 1)


def test_a_settled_request_does_not_give_up_although_it_is_old():
    assert decision.decide(_row(state="request_succeeded", first_age=172801), NOW, {}) == ("done", 1)


def test_the_wait_window_of_an_attempt_is_the_lease():
    assert decision.wait_window(_row(), {}) == 120.0


def test_the_wait_window_of_a_failure_is_the_backoff():
    assert decision.wait_window(_row(state="request_failed"), {}) == 300


def test_a_settled_request_has_no_wait_window():
    assert decision.wait_window(_row(state="request_succeeded"), {}) == 0.0


def test_the_row_of_a_request_is_found_by_kind_and_name():
    rows = [_row(kind="jrd", name="a"), _row(kind="actor", name="b")]

    assert decision.row_for(rows, "actor", "b")["kind"] == "actor"


def test_a_request_that_was_never_made_has_no_row():
    assert decision.row_for([_row(kind="jrd", name="a")], "jrd", "b") is None


def test_the_same_name_of_another_kind_is_not_confused():
    assert decision.row_for([_row(kind="jrd", name="a")], "actor", "a") is None


def test_the_first_ordinal_of_a_kind_is_one():
    assert decision.next_ordinal([], "jrd") == 1


def test_the_next_ordinal_follows_the_highest():
    rows = [_row(kind="jrd", ordinal=1), _row(kind="jrd", ordinal=3), _row(kind="actor", ordinal=9)]

    assert decision.next_ordinal(rows, "jrd") == 4


def test_the_ordinals_of_the_kinds_are_counted_apart():
    rows = [_row(kind="jrd", ordinal=5)]

    assert decision.next_ordinal(rows, "actor") == 1

