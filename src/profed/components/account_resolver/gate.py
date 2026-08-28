# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime


def _make_gate():
    current_names = {}
    cache_time = None

    def init(config: dict) -> None:
        nonlocal cache_time
        cache_time = config["resolution_cache"]
        current_names.clear()

    def has_expired(resolved_at: datetime | None, event_time: datetime) -> bool:
        return resolved_at is not None and resolved_at + cache_time < event_time

    def try_start(name: str, event_time: datetime) -> bool:
        if name in current_names and not has_expired(current_names[name], event_time):
            return False

        current_names[name] = None
        return True

    def done(name: str, event_time: datetime) -> None:
        nonlocal current_names
        current_names[name] = event_time
        current_names = {known: resolved_at
                         for known, resolved_at in current_names.items()
                         if not has_expired(resolved_at, event_time)}

    return init, has_expired, try_start, done


init, has_expired, try_start, done = _make_gate()

