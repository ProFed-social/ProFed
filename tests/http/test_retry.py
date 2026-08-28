# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from profed.http import retry


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def test_the_first_attempt_waits_the_initial_interval():
    assert retry.backoff(1, {}) == retry.INITIAL_RETRY


def test_every_attempt_doubles_the_wait():
    assert retry.backoff(3, {}) == retry.INITIAL_RETRY * 4


def test_the_wait_is_capped():
    assert retry.backoff(99, {}) == retry.MAX_RETRY


def test_the_interval_is_configurable():
    assert retry.backoff(1, {"initial_retry": 10}) == 10


def test_the_multiplier_is_configurable():
    assert retry.backoff(2, {"initial_retry": 10, "retry_multiplier": 3}) == 30


def test_the_cap_is_configurable():
    assert retry.backoff(99, {"max_retry": 60}) == 60


def test_due_at_adds_the_backoff_to_the_failure():
    assert retry.due_at(NOW, 1, {"initial_retry": 60}) == NOW + timedelta(seconds=60)


def test_a_fresh_attempt_is_not_exhausted():
    assert not retry.exhausted(NOW, NOW + timedelta(seconds=10), {})


def test_an_attempt_beyond_the_total_is_exhausted():
    assert retry.exhausted(NOW, NOW + timedelta(seconds=retry.MAX_TOTAL + 1), {})


def test_the_total_is_configurable():
    assert retry.exhausted(NOW, NOW + timedelta(seconds=11), {"max_total": 10})


def test_without_a_first_attempt_nothing_is_exhausted():
    assert not retry.exhausted(None, NOW, {})


def test_a_recent_attempt_still_holds_the_lease():
    assert retry.leased(NOW, NOW + timedelta(seconds=1), {})


def test_an_old_attempt_lost_the_lease():
    assert not retry.leased(NOW, NOW + timedelta(seconds=retry.LEASE + 1), {})


def test_the_lease_is_configurable():
    assert not retry.leased(NOW, NOW + timedelta(seconds=2), {"lease": 1})


def test_without_an_attempt_there_is_no_lease():
    assert not retry.leased(None, NOW, {})

