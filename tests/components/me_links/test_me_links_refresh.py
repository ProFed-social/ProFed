# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from profed.components.me_links.config import parse
from profed.components.me_links.refresh import due_at, is_due, modified_at, parse_http_date, refresh_interval


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)

CONFIG = {"min_wait": timedelta(days=1), "max_wait": timedelta(days=30), "ramp": timedelta(days=90)}


def _days(count):
    return NOW - timedelta(days=count)


def test_a_fresh_page_gets_the_minimum_interval():
    assert refresh_interval(timedelta(0), CONFIG) == timedelta(days=1)


def test_an_old_page_gets_the_maximum_interval():
    assert refresh_interval(timedelta(days=90), CONFIG) == timedelta(days=30)


def test_a_page_older_than_the_ramp_stays_at_the_maximum():
    assert refresh_interval(timedelta(days=365), CONFIG) == timedelta(days=30)


def test_the_interval_grows_with_the_age():
    assert refresh_interval(timedelta(days=45), CONFIG) > refresh_interval(timedelta(days=7), CONFIG)


def test_a_valid_http_date_is_parsed():
    assert parse_http_date("Sat, 30 Aug 2026 08:00:00 GMT") is not None


def test_nonsense_is_no_http_date():
    assert parse_http_date("gestern") is None


def test_a_missing_http_date_is_none():
    assert parse_http_date(None) is None


def test_the_last_modified_header_gives_the_age():
    row = {"last_modified": "Sat, 23 Aug 2026 12:00:00 GMT", "stable_since": _days(1)}

    assert modified_at(row, NOW) == datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def test_a_last_modified_in_the_future_is_ignored():
    row = {"last_modified": "Sun, 30 Aug 2027 12:00:00 GMT", "stable_since": _days(5)}

    assert modified_at(row, NOW) == _days(5)


def test_without_last_modified_the_stability_counts():
    assert modified_at({"stable_since": _days(5)}, NOW) == _days(5)


def test_a_check_is_due_after_its_interval():
    row = {"checked_at": _days(2), "stable_since": _days(2), "last_modified": None}

    assert is_due(row, CONFIG, NOW) is True


def test_a_recent_check_is_not_due():
    row = {"checked_at": NOW - timedelta(hours=1), "stable_since": _days(2), "last_modified": None}

    assert is_due(row, CONFIG, NOW) is False


def test_a_stable_page_is_checked_later_than_a_fresh_one():
    stable = {"checked_at": NOW, "stable_since": _days(60), "last_modified": None}
    fresh = {"checked_at": NOW, "stable_since": NOW, "last_modified": None}

    assert due_at(stable, CONFIG, NOW) > due_at(fresh, CONFIG, NOW)


def test_the_waits_come_from_the_configuration():
    parsed = parse({"min_wait": 60, "max_wait": 600, "ramp_days": 7}, {})

    assert parsed["min_wait"] == timedelta(seconds=60)
    assert parsed["max_wait"] == timedelta(seconds=600)
    assert parsed["ramp"] == timedelta(days=7)


def test_the_waits_have_defaults():
    parsed = parse({}, {})

    assert parsed["min_wait"] == timedelta(days=1)
    assert parsed["max_wait"] == timedelta(days=30)
    assert parsed["ramp"] == timedelta(days=90)

