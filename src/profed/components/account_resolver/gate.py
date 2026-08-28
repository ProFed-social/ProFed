# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone


def _make_gate():
    current_names = {}
    cache_time = None

    def init(config: dict) -> None:
        nonlocal cache_time
        cache_time = config["resolution_cache"]
        current_names.clear()

    def has_expired(resolved_at: datetime | None, now: datetime) -> bool:
        return resolved_at is not None and resolved_at + cache_time < now

    def try_start(name: str) -> bool:
        if name in current_names and not has_expired(current_names[name], datetime.now(timezone.utc)):
            return False

        current_names[name] = None
        return True

    def done(name: str) -> None:
        nonlocal current_names
        now = datetime.now(timezone.utc)
        current_names[name] = now
        current_names = {known: resolved_at
                         for known, resolved_at in current_names.items()
                         if not has_expired(resolved_at, now)}

    return init, has_expired, try_start, done


init, has_expired, try_start, done = _make_gate()

