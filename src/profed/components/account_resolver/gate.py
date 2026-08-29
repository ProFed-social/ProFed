# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta


def _make_gate():
    valid_until = {}
    lifetimes = {}

    def init(config: dict) -> None:
        lifetimes.clear()
        lifetimes.update({"resolved": config["resolution_cache"], "unresolved": config["unresolved_cache"]})
        valid_until.clear()

    def has_expired(expires_at: datetime | None, event_time: datetime) -> bool:
        return expires_at is not None and expires_at < event_time

    def try_start(name: str, event_time: datetime) -> bool:
        if name in valid_until and not has_expired(valid_until[name], event_time):
            return False

        valid_until[name] = None
        return True

    def lifetime(state: str) -> timedelta:
        return lifetimes.get(state, lifetimes["resolved"])

    def done(name: str, event_time: datetime, state: str = "resolved") -> None:
        valid_until[name] = event_time + lifetime(state)
        expired = [known for known, expires_at in valid_until.items() if has_expired(expires_at, event_time)]
        for known in expired:
            del valid_until[known]

    return init, has_expired, try_start, done


init, has_expired, try_start, done = _make_gate()

