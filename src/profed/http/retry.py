# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta


INITIAL_RETRY = 300
RETRY_MULTIPLIER = 2
MAX_RETRY = 86400
MAX_TOTAL = 172800
LEASE = 120.0


def backoff(attempt: int, config: dict) -> float:
    return min(int(config.get("initial_retry", INITIAL_RETRY))
               * float(config.get("retry_multiplier", RETRY_MULTIPLIER)) ** (attempt - 1),
               int(config.get("max_retry", MAX_RETRY)))


def due_at(failed_at: datetime, attempt: int, config: dict) -> datetime:
    return failed_at + timedelta(seconds=backoff(attempt, config))


def exhausted(first_attempt_at: datetime, now: datetime, config: dict) -> bool:
    return (first_attempt_at is not None
            and (now - first_attempt_at).total_seconds() > int(config.get("max_total", MAX_TOTAL)))


def leased(attempt_at: datetime, now: datetime, config: dict) -> bool:
    return attempt_at is not None and now < attempt_at + timedelta(seconds=float(config.get("lease", LEASE)))

