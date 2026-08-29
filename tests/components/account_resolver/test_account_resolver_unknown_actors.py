# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
import pytest
from profed.components.account_resolver import gate, unknown_actors
from profed.components.account_resolver import storage as storage_module


UNRESOLVED = timedelta(days=4)
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self, rows=None):
        self.rows = rows or []

    async def unfinished(self):
        return self.rows


@pytest.fixture(autouse=True)
def component():
    backup_storage = storage_module._instance
    backup_workers = unknown_actors._workers
    storage_module._instance = FakeStorage()
    unknown_actors._workers = _FakeWorkers()
    gate.init({"resolution_cache": timedelta(seconds=300), "unresolved_cache": UNRESOLVED})
    yield storage_module._instance
    storage_module._instance = backup_storage
    unknown_actors._workers = backup_workers


class _FakeWorkers:
    def __init__(self):
        self.submitted = []
        self.started = False

    def submit(self, key, item=None):
        self.submitted.append((key, item))

    def start(self, keys=()):
        self.started = True


@pytest.mark.asyncio
async def test_a_discovered_acct_is_submitted():
    await unknown_actors._requested("alice@a.test", {}, NOW, 7)

    assert unknown_actors._workers.submitted == [(("unknown_actors", 7), "alice@a.test")]


@pytest.mark.asyncio
async def test_a_discovered_url_is_submitted():
    await unknown_actors._requested("https://a.test/actors/alice", {}, NOW, 9)

    assert unknown_actors._workers.submitted == [(("unknown_actors", 9), "https://a.test/actors/alice")]


@pytest.mark.asyncio
async def test_a_name_the_gate_blocks_is_not_submitted():
    gate.try_start("alice@a.test", NOW)

    await unknown_actors._requested("alice@a.test", {}, NOW, 7)

    assert unknown_actors._workers.submitted == []


@pytest.mark.asyncio
async def test_two_events_for_the_same_name_submit_once():
    await unknown_actors._requested("alice@a.test", {}, NOW, 7)
    await unknown_actors._requested("alice@a.test", {}, NOW, 8)

    assert len(unknown_actors._workers.submitted) == 1


@pytest.mark.asyncio
async def test_every_process_gets_its_own_worker_key():
    await unknown_actors._requested("alice@a.test", {}, NOW, 7)
    await unknown_actors._requested("bob@b.test", {}, NOW, 8)

    assert [key for key, _ in unknown_actors._workers.submitted] == [("unknown_actors", 7), ("unknown_actors", 8)]


@pytest.mark.asyncio
async def test_resuming_submits_the_unfinished_processes(component):
    component.rows = [{"source": "unknown_actors", "sequence_id": 7, "entry": "alice@a.test", "emitted_at": NOW},
                      {"source": "raw_activities", "sequence_id": 3, "entry": "bob@b.test", "emitted_at": NOW}]

    assert await unknown_actors.resume() == 2
    assert unknown_actors._workers.submitted == [(("unknown_actors", 7), "alice@a.test"),
                                                 (("raw_activities", 3), "bob@b.test")]


@pytest.mark.asyncio
async def test_resuming_keeps_the_source_of_every_process(component):
    component.rows = [{"source": "raw_activities", "sequence_id": 3, "entry": "bob@b.test", "emitted_at": NOW}]

    await unknown_actors.resume()

    assert unknown_actors._workers.submitted[0][0] == ("raw_activities", 3)


@pytest.mark.asyncio
async def test_resuming_closes_the_gate_for_what_it_started(component):
    component.rows = [{"source": "unknown_actors", "sequence_id": 7, "entry": "alice@a.test", "emitted_at": NOW}]

    await unknown_actors.resume()

    assert gate.try_start("alice@a.test", NOW) is False


@pytest.mark.asyncio
async def test_resuming_skips_what_is_already_running(component):
    component.rows = [{"source": "unknown_actors", "sequence_id": 7, "entry": "alice@a.test", "emitted_at": NOW}]
    gate.try_start("alice@a.test", NOW)

    assert await unknown_actors.resume() == 0
    assert unknown_actors._workers.submitted == []


@pytest.mark.asyncio
async def test_resuming_without_unfinished_processes_submits_nothing(component):
    assert await unknown_actors.resume() == 0
    assert unknown_actors._workers.submitted == []

