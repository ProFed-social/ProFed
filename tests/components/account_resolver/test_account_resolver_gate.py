# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
import pytest
from profed.components.account_resolver.config import parse
from profed.components.account_resolver.gate import done, has_expired, init, try_start


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

CACHE = timedelta(seconds=300)
UNRESOLVED = timedelta(days=4)


def _later(seconds):
    return NOW + timedelta(seconds=seconds)


@pytest.fixture(autouse=True)
def gate():
    init({"resolution_cache": CACHE, "unresolved_cache": UNRESOLVED})


def test_an_unknown_name_starts():
    assert try_start("alice@a.test", NOW)


def test_a_running_name_does_not_start_again():
    try_start("alice@a.test", NOW)

    assert not try_start("alice@a.test", _later(1))


def test_a_running_name_stays_blocked_beyond_the_cache_time():
    try_start("alice@a.test", NOW)

    assert not try_start("alice@a.test", _later(301))


def test_a_recently_finished_name_does_not_start():
    try_start("alice@a.test", NOW)
    done("alice@a.test", NOW)

    assert not try_start("alice@a.test", _later(299))


def test_a_name_beyond_the_cache_time_starts_again():
    try_start("alice@a.test", NOW)
    done("alice@a.test", NOW)

    assert try_start("alice@a.test", _later(301))


def test_a_restarted_name_blocks_a_third_start():
    try_start("alice@a.test", NOW)
    done("alice@a.test", NOW)

    try_start("alice@a.test", _later(301))
    assert not try_start("alice@a.test", _later(302))


def test_finishing_keeps_names_that_are_still_running():
    try_start("alice@a.test", NOW)

    done("bob@b.test", _later(301))
    assert not try_start("alice@a.test", _later(302))


def test_finishing_keeps_names_within_the_cache_time():
    try_start("alice@a.test", NOW)
    done("alice@a.test", NOW)

    done("bob@b.test", _later(10))
    assert not try_start("alice@a.test", _later(10))


def test_nothing_has_expired_without_a_time():
    assert not has_expired(None, NOW)


def test_a_deadline_in_the_future_has_not_expired():
    assert not has_expired(_later(300), NOW)


def test_a_deadline_in_the_past_has_expired():
    assert has_expired(NOW, _later(1))


def test_the_cache_time_comes_from_the_configuration():
    init({"resolution_cache": timedelta(seconds=10), "unresolved_cache": UNRESOLVED})
    done("alice@a.test", NOW)

    assert try_start("alice@a.test", _later(9)) is False
    assert try_start("alice@a.test", _later(11)) is True


def test_an_unresolved_name_stays_blocked_much_longer():
    init({"resolution_cache": timedelta(seconds=10), "unresolved_cache": timedelta(seconds=1000)})
    done("alice@a.test", NOW, "unresolved")

    assert try_start("alice@a.test", _later(11)) is False
    assert try_start("alice@a.test", _later(1001)) is True


def test_a_resolved_name_uses_the_short_time():
    init({"resolution_cache": timedelta(seconds=10), "unresolved_cache": timedelta(seconds=1000)})
    done("alice@a.test", NOW, "resolved")

    assert try_start("alice@a.test", _later(11)) is True


def test_an_unknown_state_falls_back_to_the_short_time():
    init({"resolution_cache": timedelta(seconds=10), "unresolved_cache": timedelta(seconds=1000)})
    done("alice@a.test", NOW, "something_else")

    assert try_start("alice@a.test", _later(11)) is True


def test_the_unresolved_time_comes_from_the_configuration():
    assert parse({"unresolved_cache": 99}, {})["unresolved_cache"] == timedelta(seconds=99)


def test_the_unresolved_time_defaults_to_four_days():
    assert parse({}, {})["unresolved_cache"] == timedelta(days=4)


def test_initialisation_forgets_what_was_running():
    try_start("alice@a.test", NOW)

    init({"resolution_cache": CACHE, "unresolved_cache": UNRESOLVED})

    assert try_start("alice@a.test", _later(1))


def test_the_configuration_turns_the_cache_time_into_a_timedelta():
    assert parse({"resolution_cache": 42}, {})["resolution_cache"] == timedelta(seconds=42)


def test_the_configuration_defaults_the_cache_time():
    assert parse({}, {})["resolution_cache"] == CACHE


def test_the_configuration_keeps_the_other_entries():
    assert parse({"whatever": 1}, {})["whatever"] == 1

