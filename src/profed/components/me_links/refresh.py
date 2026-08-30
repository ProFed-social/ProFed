# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime


def parse_http_date(value) -> datetime | None:
    try:
        return parsedate_to_datetime(value) if value else None
    except (TypeError, ValueError):
        return None


def modified_at(row: dict, now: datetime) -> datetime:
    stated = parse_http_date((row or {}).get("last_modified"))
    return (stated
            if stated is not None and stated <= now else
            (row or {}).get("stable_since") or now)


def refresh_interval(age: timedelta, config: dict) -> timedelta:
    minimum, maximum, ramp = config["min_wait"], config["max_wait"], config["ramp"]
    return min(maximum, minimum + (maximum - minimum) * (age / ramp))


def due_at(row: dict, config: dict, now: datetime) -> datetime:
    return row["checked_at"] + refresh_interval(now - modified_at(row, now), config)


def is_due(row: dict, config: dict, now: datetime) -> bool:
    return due_at(row, config, now) <= now

