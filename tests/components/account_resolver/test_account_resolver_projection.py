# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from datetime import datetime, timezone
import pytest
from profed.components.account_resolver import projection
from profed.components.account_resolver import storage as storage_module
from profed.components.account_resolver.resolve import NeedsRequest


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

JRD = {"subject": "acct:alice@a.test"}


class FakeStorage:
    def __init__(self):
        self.processes = []
        self.ensured = []
        self.requests_recorded = []

    async def record_process(self, source, sequence_id, entry, state, emitted_at):
        self.processes.append((source, sequence_id, entry, state, emitted_at))

    async def ensure_process(self, source, sequence_id, entry, emitted_at):
        self.ensured.append((source, sequence_id, entry, emitted_at))

    async def record_request(self, source, sequence_id, kind, ordinal, state, attempt, name, document, emitted_at):
        self.requests_recorded.append((source, sequence_id, kind, ordinal, state, attempt, name, document))


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _payload(**overrides):
    return {"source": "unknown_actors", "sequence_id": 7, "kind": "jrd", "ordinal": 1, **overrides}


@pytest.mark.asyncio
async def test_an_attempt_is_recorded_as_a_request(fake_storage):
    await projection._record("attempting", "alice@a.test", _payload(attempt=1), NOW)

    assert fake_storage.requests_recorded[0][:6] == ("unknown_actors", 7, "jrd", 1, "attempting", 1)
    assert fake_storage.processes == []


@pytest.mark.asyncio
async def test_a_succeeded_request_stores_its_document(fake_storage):
    await projection._record("request_succeeded", "alice@a.test", _payload(name="alice@a.test", document=JRD), NOW)

    assert json.loads(fake_storage.requests_recorded[0][7]) == JRD


@pytest.mark.asyncio
async def test_a_tombstone_stores_its_document(fake_storage):
    await projection._record("request_tombstone", "alice@a.test", _payload(document={"type": "Tombstone"}), NOW)

    assert json.loads(fake_storage.requests_recorded[0][7]) == {"type": "Tombstone"}


@pytest.mark.asyncio
async def test_a_failed_request_stores_no_document(fake_storage):
    await projection._record("request_failed", "alice@a.test", _payload(attempt=2, document=JRD), NOW)

    assert fake_storage.requests_recorded[0][7] is None


@pytest.mark.asyncio
async def test_a_request_makes_its_process_known(fake_storage):
    await projection._record("attempting", "alice@a.test", _payload(attempt=1), NOW)
    assert fake_storage.ensured == [("unknown_actors", 7, "alice@a.test", NOW)]


@pytest.mark.asyncio
async def test_a_process_event_does_not_ensure_the_process(fake_storage):
    await projection._record("resolved", "alice@a.test", {"source": "unknown_actors", "sequence_id": 7}, NOW)
    assert fake_storage.ensured == []


@pytest.mark.asyncio
async def test_a_resolved_process_is_recorded_as_a_process(fake_storage):
    await projection._record("resolved", "alice@a.test", {"source": "unknown_actors", "sequence_id": 7}, NOW)

    assert fake_storage.processes == [("unknown_actors", 7, "alice@a.test", "resolved", NOW)]
    assert fake_storage.requests_recorded == []


@pytest.mark.asyncio
async def test_an_unresolved_process_is_recorded_as_a_process(fake_storage):
    await projection._record("unresolved", "alice@a.test", {"source": "unknown_actors", "sequence_id": 7}, NOW)

    assert fake_storage.processes[0][3] == "unresolved"


def test_a_succeeded_request_becomes_a_known_document():
    known = projection.known_from([{"kind": "jrd", "ordinal": 1, "state": "request_succeeded",
                                    "name": "alice@a.test", "document": json.dumps(JRD)}])

    assert known.get("jrd", "alice@a.test") == JRD


def test_a_not_found_request_becomes_a_known_absence():
    known = projection.known_from([{"kind": "jrd", "ordinal": 1, "state": "request_not_found",
                                    "name": "alice@a.test", "document": None}])

    assert known.get("jrd", "alice@a.test") is None


def test_a_tombstone_becomes_a_known_absence():
    known = projection.known_from([{"kind": "actor", "ordinal": 1, "state": "request_tombstone",
                                    "name": "https://a.test/x", "document": json.dumps({"type": "Tombstone"})}])

    assert known.get("actor", "https://a.test/x") is None


def test_a_failed_request_stays_unknown():
    known = projection.known_from([{"kind": "jrd", "ordinal": 1, "state": "request_failed",
                                    "name": "alice@a.test", "document": None}])

    with pytest.raises(NeedsRequest):
        known.get("jrd", "alice@a.test")


def test_a_pending_attempt_stays_unknown():
    known = projection.known_from([{"kind": "jrd", "ordinal": 1, "state": "attempting",
                                    "name": "alice@a.test", "document": None}])

    with pytest.raises(NeedsRequest):
        known.get("jrd", "alice@a.test")


def test_known_keeps_the_two_kinds_apart():
    rows = [{"kind": "jrd", "ordinal": 1, "state": "request_succeeded", "name": "x", "document": json.dumps(JRD)},
            {"kind": "actor", "ordinal": 1, "state": "request_not_found", "name": "x", "document": None}]

    known = projection.known_from(rows)

    assert known.get("jrd", "x") == JRD
    assert known.get("actor", "x") is None


def test_the_ordinals_of_an_empty_process_are_zero():
    assert projection.ordinals([]) == {"jrd": 0, "actor": 0}


def test_the_ordinals_report_the_highest_number_per_kind():
    rows = [{"kind": "jrd", "ordinal": 1, "state": "request_succeeded", "name": "a", "document": None},
            {"kind": "jrd", "ordinal": 3, "state": "request_succeeded", "name": "b", "document": None},
            {"kind": "actor", "ordinal": 2, "state": "attempting", "name": "c", "document": None}]

    assert projection.ordinals(rows) == {"jrd": 3, "actor": 2}

