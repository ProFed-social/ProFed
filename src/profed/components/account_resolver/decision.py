# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timedelta
from profed.http.retry import backoff, exhausted


_RETRIABLE = ("attempting", "request_failed")


def wait_window(row, config: dict) -> float:
    return (float(config.get("lease", 120.0))
            if row["state"] == "attempting" else
            backoff(row["attempt"], config)
            if row["state"] == "request_failed" else
            0.0)


def decide(row, now, config: dict) -> tuple:
    return (("claim", 1)
            if row is None else
            ("done", row["attempt"])
            if row["state"] not in _RETRIABLE else
            ("give_up", row["attempt"])
            if exhausted(row["first_attempt_at"], now, config) else
            ("claim", row["attempt"] + 1)
            if now >= row["emitted_at"] + timedelta(seconds=wait_window(row, config)) else
            ("wait", row["attempt"]))


def row_for(rows, kind: str, name: str):
    return next((row for row in rows if row["kind"] == kind and row["name"] == name), None)


def next_ordinal(rows, kind: str) -> int:
    return max((row["ordinal"] for row in rows if row["kind"] == kind), default=0) + 1

