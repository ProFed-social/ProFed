# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import AsyncMock, patch
from profed.components.account_resolver import storage as storage_module
from profed.components.account_resolver import gate, worker
from profed import identity
from profed.identity import account_id


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

ALICE_URL = "https://a.test/actors/alice"

JRD = {"subject": "acct:alice@a.test",
       "links": [{"rel": "self", "type": "application/activity+json", "href": ALICE_URL}]}

ACTOR = {"id": ALICE_URL, "type": "Person", "preferredUsername": "alice"}


class FakeStorage:
    def __init__(self):
        self.rows = []
        self.processes = {}

    async def requests(self, source, sequence_id):
        return self.rows

    async def process(self, source, sequence_id):
        return self.processes.get((source, sequence_id))


@pytest.fixture(autouse=True)
def component():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    worker.configure({})
    gate.init({"resolution_cache": timedelta(seconds=300)})
    with patch.object(identity, "domain", lambda: "local.test"):
        yield storage_module._instance
    storage_module._instance = backup


def _row(kind, name, state, ordinal=1, attempt=1, document=None, age=0, first_age=0):
    return {"kind": kind,
            "ordinal": ordinal,
            "state": state,
            "attempt": attempt,
            "name": name,
            "document": json.dumps(document) if document is not None else None,
            "first_attempt_at": NOW - timedelta(seconds=first_age),
            "emitted_at": NOW - timedelta(seconds=age)}


@contextmanager
def _at(moment):
    with patch.object(worker, "datetime") as clock:
        clock.now.return_value = moment
        yield


def _queue(*items):
    queue = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    return queue


def _published(fake_bus):
    return [(p["event_type"], p["payload"].get("kind"), p["payload"].get("name"))
            for p in fake_bus.topic("account_resolution").published]


@pytest.mark.asyncio
async def test_a_new_process_claims_its_first_webfinger(fake_bus, component):
    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_succeeded", JRD))):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == [("attempting", "jrd", "alice@a.test"),
                                    ("request_succeeded", "jrd", "alice@a.test")]


@pytest.mark.asyncio
async def test_the_request_is_performed_with_the_kind_and_name_the_chain_asked_for(fake_bus, component):
    perform = AsyncMock(return_value=("request_succeeded", JRD))
    with _at(NOW), patch.object(worker.fetch, "perform", perform):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert perform.await_args.args[:2] == ("jrd", "alice@a.test")


@pytest.mark.asyncio
async def test_a_known_webfinger_leads_to_the_actor_request(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_succeeded", document=JRD)]

    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_succeeded", ACTOR))):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == [("attempting", "actor", ALICE_URL),
                                    ("request_succeeded", "actor", ALICE_URL)]


@pytest.mark.asyncio
async def test_a_complete_chain_resolves_the_process(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_succeeded", document=JRD),
                      _row("actor", ALICE_URL, "request_succeeded", document=ACTOR)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == [("resolved", None, None)]


@pytest.mark.asyncio
async def test_an_impossible_chain_leaves_the_process_unresolved(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_not_found")]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == [("unresolved", None, None)]


@pytest.mark.asyncio
async def test_a_waiting_request_publishes_nothing(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "attempting", age=10)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_a_failed_request_past_its_backoff_is_retried(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_failed", age=301)]

    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_failed", None))):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == [("attempting", "jrd", "alice@a.test"),
                                    ("request_failed", "jrd", "alice@a.test")]


@pytest.mark.asyncio
async def test_a_retry_counts_up(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_failed", age=301)]

    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_failed", None))):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert fake_bus.topic("account_resolution").published[0]["payload"]["attempt"] == 2


@pytest.mark.asyncio
async def test_a_retry_keeps_the_ordinal_of_its_request(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_failed", ordinal=3, age=301)]

    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_failed", None))):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert fake_bus.topic("account_resolution").published[0]["payload"]["ordinal"] == 3


@pytest.mark.asyncio
async def test_an_exhausted_request_leaves_the_process_unresolved(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_failed", first_age=172801, age=100000)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == [("unresolved", None, None)]


@pytest.mark.asyncio
async def test_a_lost_claim_performs_no_request(fake_bus, component):
    perform = AsyncMock(return_value=("request_succeeded", JRD))
    with _at(NOW), patch.object(worker.fetch, "perform", perform):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))
        fake_bus.topic("account_resolution").published.clear()
        component.rows = []
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _published(fake_bus) == []
    assert perform.await_count == 1


@pytest.mark.asyncio
async def test_a_finished_process_is_not_advanced(fake_bus, component):
    component.processes[("unknown_actors", 7)] = {"entry": "alice@a.test", "state": "resolved"}

    with _at(NOW):
        assert await worker.step(("unknown_actors", 7), _queue("alice@a.test")) is False
    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_a_step_that_did_something_reports_work(fake_bus, component):
    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_succeeded", JRD))):
        assert await worker.step(("unknown_actors", 7), _queue("alice@a.test")) is True


@pytest.mark.asyncio
async def test_the_entry_is_taken_from_the_stored_process_when_the_queue_is_empty(fake_bus, component):
    component.processes[("unknown_actors", 7)] = {"entry": "alice@a.test", "state": "attempting"}

    with _at(NOW), patch.object(worker.fetch, "perform", AsyncMock(return_value=("request_succeeded", JRD))):
        await worker.step(("unknown_actors", 7), _queue())

    assert _published(fake_bus)[0] == ("attempting", "jrd", "alice@a.test")


@pytest.mark.asyncio
async def test_finishing_a_process_releases_the_gate(fake_bus, component):
    gate.init({"resolution_cache": timedelta(seconds=0)})
    component.rows = [_row("jrd", "alice@a.test", "request_not_found")]
    gate.try_start("alice@a.test")

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert gate.try_start("alice@a.test") is True


@pytest.mark.asyncio
async def test_an_unfinished_process_keeps_the_gate_closed(fake_bus, component):
    gate.init({"resolution_cache": timedelta(seconds=0)})
    component.rows = [_row("jrd", "alice@a.test", "attempting", age=10)]
    gate.try_start("alice@a.test")

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert gate.try_start("alice@a.test") is False


@pytest.mark.asyncio
async def test_the_signer_comes_from_the_instance_key(fake_bus, component):
    perform = AsyncMock(return_value=("request_succeeded", JRD))
    with _at(NOW), \
         patch.object(worker.instance_key, "signing_key", lambda: ("https://a.test/actor#main-key", "PEM")), \
         patch.object(worker, "make_sign", lambda *args: "signer"), \
         patch.object(worker.fetch, "perform", perform):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert perform.await_args.args[2] == "signer"


@pytest.mark.asyncio
async def test_without_an_instance_key_nothing_is_signed(fake_bus, component):
    perform = AsyncMock(return_value=("request_succeeded", JRD))
    with _at(NOW), \
         patch.object(worker.instance_key, "signing_key", lambda: None), \
         patch.object(worker.fetch, "perform", perform):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert perform.await_args.args[2] is None


def _registered(fake_bus):
    return fake_bus.topic("remote_actors").published


@pytest.mark.asyncio
async def test_a_resolved_process_registers_its_actor(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_succeeded", document=JRD),
                      _row("actor", ALICE_URL, "request_succeeded", document=ACTOR)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _registered(fake_bus)[0]["event_type"] == "discovered"
    assert _registered(fake_bus)[0]["payload"]["acct"] == "alice@a.test"
    assert _registered(fake_bus)[0]["payload"]["actor_url"] == ALICE_URL
    assert _registered(fake_bus)[0]["payload"]["actor_data"] == ACTOR


@pytest.mark.asyncio
async def test_the_registration_is_keyed_by_the_account_id(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_succeeded", document=JRD),
                      _row("actor", ALICE_URL, "request_succeeded", document=ACTOR)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _registered(fake_bus)[0]["object_id"] == str(int(account_id("alice@a.test")))


@pytest.mark.asyncio
async def test_the_registration_carries_the_confirmed_aliases(fake_bus, component):
    other = {"subject": "acct:chris@okunah.de",
             "links": [{"rel": "self", "type": "application/activity+json", "href": ALICE_URL}]}
    component.rows = [_row("jrd", "chris@okunah.de", "request_succeeded", document=other),
                      _row("jrd", "alice@a.test", "request_succeeded", ordinal=2, document=JRD),
                      _row("actor", ALICE_URL, "request_succeeded", document=ACTOR)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("chris@okunah.de"))

    assert _registered(fake_bus)[0]["payload"]["acct"] == "alice@a.test"
    assert _registered(fake_bus)[0]["payload"]["acct_aliases"] == ["chris@okunah.de"]


@pytest.mark.asyncio
async def test_the_registration_notes_when_the_webfinger_was_read(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_succeeded", document=JRD),
                      _row("actor", ALICE_URL, "request_succeeded", document=ACTOR)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _registered(fake_bus)[0]["payload"]["last_webfinger_at"] == NOW.isoformat()


@pytest.mark.asyncio
async def test_an_unresolved_process_registers_nothing(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_not_found")]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert _registered(fake_bus) == []


@pytest.mark.asyncio
async def test_a_local_account_is_not_registered_as_remote(fake_bus, component):
    local_url = "https://local.test/actors/alice"
    jrd = {"subject": "acct:alice@local.test",
           "links": [{"rel": "self", "type": "application/activity+json", "href": local_url}]}
    component.rows = [_row("jrd", "alice@local.test", "request_succeeded", document=jrd),
                      _row("actor", local_url, "request_succeeded",
                           document={"id": local_url, "type": "Person", "preferredUsername": "alice"})]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@local.test"))

    assert _registered(fake_bus) == []


@pytest.mark.asyncio
async def test_a_remote_account_is_registered(fake_bus, component):
    component.rows = [_row("jrd", "alice@a.test", "request_succeeded", document=JRD),
                      _row("actor", ALICE_URL, "request_succeeded", document=ACTOR)]

    with _at(NOW):
        await worker.step(("unknown_actors", 7), _queue("alice@a.test"))

    assert len(_registered(fake_bus)) == 1

