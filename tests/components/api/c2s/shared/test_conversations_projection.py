# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.shared.conversations import projection, storage


DIRECT = {"created_at": "2026-01-01T00:00:00.000Z",
          "visibility": "direct",
          "in_reply_to_id": "https://remote/notes/root",
          "mentions": [{"url": "https://s/bob"}, {"url": "https://s/carol"}]}

PUBLIC = {"created_at": "2026-01-01T00:00:00.000Z",
          "visibility": "public",
          "in_reply_to_id": None,
          "mentions": []}


class RecordingStorage:
    def __init__(self):
        self.records: list[tuple] = []

    async def ensure_schema(self) -> None:
        pass

    async def record(self, *args) -> None:
        self.records.append(args)

    def rebuild_finished(self) -> None:
        pass


@pytest.fixture
def fake_conversations():
    backup = storage._instance
    storage._instance = RecordingStorage()

    yield storage._instance

    storage._instance = backup


@pytest.mark.asyncio
async def test_records_a_direct_message(fake_conversations):
    await projection._on_store("obj", {"status_id": "https://remote/notes/1",
                                       "actor_url": "https://s/alice",
                                       "status": DIRECT})

    assert fake_conversations.records == [("https://remote/notes/1",
                                           "https://remote/notes/root",
                                           "2026-01-01T00:00:00.000Z",
                                           "https://s/alice",
                                           ["https://s/bob", "https://s/carol"])]


@pytest.mark.asyncio
async def test_skips_a_non_direct_message(fake_conversations):
    await projection._on_store("obj", {"status_id": "https://remote/notes/2",
                                       "actor_url": "https://s/alice",
                                       "status": PUBLIC})

    assert fake_conversations.records == []

