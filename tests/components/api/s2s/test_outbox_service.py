# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from profed.components.api.s2s.outbox import storage
from profed.components.api.s2s.outbox.service import resolve_note


NOTE_URL = "https://example.com/actors/alice/notes/abc"

DELETED_AT = datetime(2026, 8, 24, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = Mock()
    storage._instance.latest_for_object = AsyncMock()

    yield storage._instance

    storage._instance = backup


@pytest.mark.asyncio
async def test_resolve_note_returns_the_note_object(fake_storage):
    note = {"id": NOTE_URL, "type": "Note", "content": "hi"}
    fake_storage.latest_for_object.return_value = {"type": "Create",
                                                   "object": note,
                                                   "created_at": DELETED_AT}

    result = await resolve_note("alice", "abc")

    fake_storage.latest_for_object.assert_awaited_once_with("alice", NOTE_URL)
    assert result == note


@pytest.mark.asyncio
async def test_resolve_note_returns_the_edited_note_after_an_update(fake_storage):
    edited = {"id": NOTE_URL, "type": "Note", "content": "edited"}
    fake_storage.latest_for_object.return_value = {"type": "Update",
                                                   "object": edited,
                                                   "created_at": DELETED_AT}

    assert await resolve_note("alice", "abc") == edited


@pytest.mark.asyncio
async def test_resolve_note_returns_a_tombstone_after_a_delete(fake_storage):
    fake_storage.latest_for_object.return_value = {"type": "Delete",
                                                   "object": NOTE_URL,
                                                   "created_at": DELETED_AT}

    result = await resolve_note("alice", "abc")

    assert result == {"@context": "https://www.w3.org/ns/activitystreams",
                      "id": NOTE_URL,
                      "type": "Tombstone",
                      "deleted": "2026-08-24T10:00:00+00:00"}


@pytest.mark.asyncio
async def test_resolve_note_returns_none_for_an_unknown_note(fake_storage):
    fake_storage.latest_for_object.return_value = None

    assert await resolve_note("alice", "abc") is None

