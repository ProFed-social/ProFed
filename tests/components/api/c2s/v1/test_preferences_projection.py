# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from asyncpg import ForeignKeyViolationError
from profed.components.api.c2s.v1.accounts.preferences import projection
from profed.components.api.c2s.v1.accounts.preferences import storage as storage_module


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeStore:
    def __init__(self):
        self.rows = {}
        self.known = {"en", "de", "fr"}

    async def ensure_schema(self):
        pass

    def rebuild_finished(self):
        pass

    async def upsert(self, username, privacy, sensitive, language):
        if language is not None and language not in self.known:
            raise ForeignKeyViolationError("unknown language")
        row = self.rows.setdefault(username, {"privacy": "public",
                                             "sensitive": False,
                                             "language": "en"})
        if privacy is not None:
            row["privacy"] = privacy
        if sensitive is not None:
            row["sensitive"] = sensitive
        if language is not None:
            row["language"] = language


@pytest.fixture
def fake_store():
    store = FakeStore()
    storage_module._instance = store
    yield store
    storage_module._instance = None


def _msg(seq, event_type, object_id, payload):
    return (seq, event_type, object_id, TS, payload)


@pytest.mark.asyncio
async def test_updated_sets_fields(fake_bus, fake_store):
    fake_bus.topic("preferences").messages = [_msg(1,
                                                   "updated",
                                                   "alice",
                                                   {"privacy": "private",
                                                    "sensitive": True,
                                                    "language": "de"})]

    await projection.rebuild()

    assert fake_store.rows["alice"] == {"privacy": "private",
                                        "sensitive": True,
                                        "language": "de"}


@pytest.mark.asyncio
async def test_unknown_language_is_logged_and_ignored(fake_bus, fake_store):
    fake_bus.topic("preferences").messages = [_msg(1, "updated", "alice", {"language": "xx"})]

    await projection.rebuild()

    assert "alice" not in fake_store.rows


@pytest.mark.asyncio
async def test_snapshot_item_is_applied(fake_bus, fake_store):
    fake_bus.topic("preferences").snapshots = [(0,
                                                [{"username": "alice",
                                                  "privacy": "unlisted",
                                                  "sensitive": False,
                                                  "language": "fr"}])]

    await projection.rebuild()

    assert fake_store.rows["alice"]["privacy"] == "unlisted"
    assert fake_store.rows["alice"]["language"] == "fr"

