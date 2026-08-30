# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from profed.http.cooldown import _make_cooldown


async def _instant(seconds):
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_the_first_request_to_a_host_waits_not_at_all():
    wait_for, _, _ = _make_cooldown()

    assert await wait_for("a.test", 10.0, _instant) == 0.0


@pytest.mark.asyncio
async def test_a_second_request_to_the_same_host_waits():
    wait_for, _, _ = _make_cooldown()
    await wait_for("a.test", 10.0, _instant)

    assert await wait_for("a.test", 10.0, _instant) > 0.0


@pytest.mark.asyncio
async def test_another_host_does_not_wait():
    wait_for, _, _ = _make_cooldown()
    await wait_for("a.test", 10.0, _instant)

    assert await wait_for("b.test", 10.0, _instant) == 0.0


@pytest.mark.asyncio
async def test_the_waits_add_up_for_a_queue_of_requests():
    wait_for, _, _ = _make_cooldown()

    waits = [await wait_for("a.test", 10.0, _instant) for _ in range(3)]

    assert waits[2] > waits[1] > waits[0]


@pytest.mark.asyncio
async def test_a_request_without_a_host_never_waits():
    wait_for, _, _ = _make_cooldown()
    await wait_for("", 10.0, _instant)

    assert await wait_for("", 10.0, _instant) == 0.0


@pytest.mark.asyncio
async def test_without_an_interval_nothing_waits():
    wait_for, _, _ = _make_cooldown()
    await wait_for("a.test", 0, _instant)

    assert await wait_for("a.test", 0, _instant) == 0.0


@pytest.mark.asyncio
async def test_concurrent_requests_to_one_host_are_serialised():
    wait_for, _, _ = _make_cooldown()

    waits = await asyncio.gather(*(wait_for("a.test", 10.0, _instant) for _ in range(4)))

    assert sorted(waits) == waits
    assert waits[0] == 0.0


@pytest.mark.asyncio
async def test_a_host_is_remembered_until_it_falls_idle():
    wait_for, known_hosts, _ = _make_cooldown()

    await wait_for("a.test", 10.0, _instant)

    assert known_hosts() == 1


@pytest.mark.asyncio
async def test_forgetting_clears_every_host():
    wait_for, known_hosts, forget_all = _make_cooldown()
    await wait_for("a.test", 10.0, _instant)

    forget_all()

    assert known_hosts() == 0

