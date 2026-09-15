# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from profed.components.reaction_collections import resolution
from profed.components.reaction_collections import storage as storage_module


NOTE = "https://remote.example/notes/7"

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

LATER = NOW + timedelta(hours=1)


class FakeStorage:
    def __init__(self):
        self.recorded = []

    async def record(self, object_url, state, checked_at, next_due_at, attempt):
        self.recorded.append({"object_url": object_url,
                              "state": state,
                              "checked_at": checked_at,
                              "next_due_at": next_due_at,
                              "attempt": attempt})


@pytest.fixture
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_a_claim_is_written_down(store):
    await resolution._on_state("attempting", NOTE, {"object_url": NOTE, "attempt": 0}, NOW)

    assert store.recorded == [{"object_url": NOTE,
                               "state": "attempting",
                               "checked_at": NOW,
                               "next_due_at": None,
                               "attempt": 0}]


@pytest.mark.asyncio
async def test_a_success_carries_the_next_turn(store):
    payload = {"object_url": NOTE, "attempt": 0, "next_due_at": LATER.isoformat()}

    await resolution._on_state("succeeded", NOTE, payload, NOW)

    assert store.recorded[0]["state"] == "succeeded"
    assert store.recorded[0]["next_due_at"] == LATER


@pytest.mark.asyncio
async def test_a_failure_carries_its_attempt(store):
    payload = {"object_url": NOTE, "attempt": 3, "next_due_at": LATER.isoformat()}

    await resolution._on_state("failed", NOTE, payload, NOW)

    assert store.recorded[0]["state"] == "failed"
    assert store.recorded[0]["attempt"] == 3
    assert store.recorded[0]["next_due_at"] == LATER


@pytest.mark.asyncio
async def test_the_object_comes_from_the_payload_not_the_subject(store):
    await resolution._on_state("attempting", "something-else", {"object_url": NOTE}, NOW)

    assert store.recorded[0]["object_url"] == NOTE

