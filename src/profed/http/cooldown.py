# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from datetime import datetime, timedelta, timezone


DEFAULT_INTERVAL = 0.2

FORGET_AFTER = timedelta(minutes=5)


def _make_cooldown():
    next_allowed = {}
    locks = {}

    def _lock(host: str) -> asyncio.Lock:
        return locks.setdefault(host, asyncio.Lock())

    def _forget_idle(now: datetime) -> None:
        idle = [host for host, free_at in next_allowed.items() if free_at + FORGET_AFTER < now]
        for host in idle:
            del next_allowed[host]
            locks.pop(host, None)

    async def wait_for(host: str, interval: float = DEFAULT_INTERVAL, sleep=asyncio.sleep) -> float:
        if not host or interval <= 0:
            return 0.0

        async with _lock(host):
            now = datetime.now(timezone.utc)
            waited = max((next_allowed.get(host, now) - now).total_seconds(), 0.0)
            if waited > 0:
                await sleep(waited)

            next_allowed[host] = now + timedelta(seconds=waited + interval)
            _forget_idle(now)
            return waited

    def known_hosts() -> int:
        return len(next_allowed)

    def forget_all() -> None:
        next_allowed.clear()
        locks.clear()

    return wait_for, known_hosts, forget_all


wait_for, known_hosts, forget_all = _make_cooldown()

