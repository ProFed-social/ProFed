# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.activity_resolver import resolution
from profed.components.activity_resolver import storage as storage_module


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self):
        self.calls: list[tuple] = []

    async def record_process(self, *a):
        self.calls.append(("record_process", a))

    async def record_version(self, *a):
        self.calls.append(("record_version", a))

    def rebuild_finished(self):
        self.calls.append(("rebuild_finished",))


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


async def test_attempting_records_process_with_its_attempt(fake_storage):
    await resolution._attempting("https://x/1", {"attempt": 2}, AT)

    assert fake_storage.calls == [("record_process", ("https://x/1", "attempting", AT, 2, 0))]


async def test_failed_records_process(fake_storage):
    await resolution._failed("https://x/1", {"attempt": 3}, AT)

    assert fake_storage.calls == [("record_process", ("https://x/1", "failed", AT, 3, 0))]


async def test_not_found_records_process_with_its_count(fake_storage):
    await resolution._not_found("https://x/1", {"attempt": 3, "not_found_count": 5}, AT)

    assert fake_storage.calls == [("record_process", ("https://x/1", "not_found", AT, 3, 5))]


async def test_succeeded_records_the_parsed_version_and_cache_end(fake_storage):
    await resolution._succeeded("https://x/1",
                                {"version": "2026-01-01T00:00:00Z", "cache_end": "2026-01-01T01:00:00Z"},
                                AT)

    verb, args = fake_storage.calls[0]
    assert verb == "record_version"
    assert args == ("https://x/1",
                    "succeeded",
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                    AT,
                    0,
                    0)


async def test_tombstone_records_its_future_version(fake_storage):
    await resolution._tombstone("https://x/1", {"version": "2026-01-05T00:00:00Z"}, AT)

    verb, args = fake_storage.calls[0]
    assert verb == "record_version"
    assert args[1] == "tombstone"
    assert args[2] == datetime(2026, 1, 5, tzinfo=timezone.utc)


async def test_a_missing_version_and_cache_end_parse_to_none(fake_storage):
    await resolution._succeeded("https://x/1", {}, AT)

    _, args = fake_storage.calls[0]
    assert args[3] is None


async def test_rebuild_unblocks_the_store_even_without_events(fake_bus, fake_storage):
    await resolution.rebuild()

    assert ("rebuild_finished",) in fake_storage.calls

