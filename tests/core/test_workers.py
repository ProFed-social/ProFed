# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from profed.core.workers import KeyedWorkers


async def _noop_sleep():
    await asyncio.sleep(0)


async def _settle(rounds=50):
    for _ in range(rounds):
        await asyncio.sleep(0)


def _recorder(seen, busy_while=0):
    async def step(key, queue):
        seen.append(key)
        if not queue.empty():
            queue.get_nowait()
            return True
        return len(seen) <= busy_while

    return step


@pytest.mark.asyncio
async def test_nothing_runs_before_start():
    seen = []
    workers = KeyedWorkers(_recorder(seen), sleep=_noop_sleep)

    workers.submit("a", "item")
    await _settle()

    assert seen == []


@pytest.mark.asyncio
async def test_a_submitted_item_reaches_the_step():
    seen = []
    workers = KeyedWorkers(_recorder(seen), sleep=_noop_sleep)
    workers.start()

    workers.submit("a", "item")
    await _settle()
    await workers.stop()

    assert "a" in seen


@pytest.mark.asyncio
async def test_the_item_arrives_in_the_queue_of_its_key():
    received = []

    async def step(key, queue):
        while not queue.empty():
            received.append((key, queue.get_nowait()))
        return bool(received)

    workers = KeyedWorkers(step, sleep=_noop_sleep)
    workers.start()

    workers.submit("a", "first")
    workers.submit("b", "second")
    await _settle()
    await workers.stop()

    assert sorted(received) == [("a", "first"), ("b", "second")]


@pytest.mark.asyncio
async def test_every_key_gets_its_own_task():
    workers = KeyedWorkers(_recorder([]), sleep=_noop_sleep)
    workers.start()

    workers.submit("a")
    workers.submit("b")

    assert set(workers._tasks) == {"a", "b"}
    await workers.stop()


@pytest.mark.asyncio
async def test_a_second_submit_does_not_spawn_a_second_task():
    workers = KeyedWorkers(_recorder([]), sleep=_noop_sleep)
    workers.start()

    workers.submit("a")
    first = workers._tasks["a"]
    workers.submit("a")

    assert workers._tasks["a"] is first
    await workers.stop()


@pytest.mark.asyncio
async def test_an_idle_worker_gives_up_its_task():
    workers = KeyedWorkers(_recorder([]), idle_limit=2, sleep=_noop_sleep)
    workers.start()

    workers.submit("a")
    await _settle()

    assert "a" not in workers._tasks


@pytest.mark.asyncio
async def test_a_worker_that_finds_work_again_keeps_running():
    calls = []

    async def step(key, queue):
        calls.append(key)
        return len(calls) != 2

    workers = KeyedWorkers(step, idle_limit=1, sleep=_noop_sleep)
    workers.start()

    workers.submit("a")
    await _settle(10)

    assert len(calls) > 3
    await workers.stop()


@pytest.mark.asyncio
async def test_start_spawns_a_task_for_every_known_key():
    workers = KeyedWorkers(_recorder([]), sleep=_noop_sleep)

    workers.start(["a", "b"])

    assert set(workers._tasks) == {"a", "b"}
    await workers.stop()


@pytest.mark.asyncio
async def test_a_failing_step_does_not_kill_the_worker():
    calls = []

    async def step(key, queue):
        calls.append(key)
        raise RuntimeError("boom")

    workers = KeyedWorkers(step, idle_limit=2, sleep=_noop_sleep)
    workers.start()

    workers.submit("a")
    await _settle(10)

    assert len(calls) > 2
    await workers.stop()


@pytest.mark.asyncio
async def test_stop_cancels_the_running_tasks():
    workers = KeyedWorkers(_recorder([]), sleep=_noop_sleep)
    workers.start()
    workers.submit("a")
    task = workers._tasks["a"]

    await workers.stop()

    assert task.cancelled() or task.done()
    assert workers._tasks == {}


@pytest.mark.asyncio
async def test_after_stop_a_submit_starts_nothing():
    workers = KeyedWorkers(_recorder([]), sleep=_noop_sleep)
    workers.start()
    await workers.stop()

    workers.submit("a")

    assert workers._tasks == {}

