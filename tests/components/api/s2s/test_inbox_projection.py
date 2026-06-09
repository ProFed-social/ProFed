# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock

from profed.core import message_bus

from profed.components.api.s2s.inbox import storage
from profed.components.api.s2s.inbox.projection import rebuild, reset_last_seen


@pytest.fixture
def fake_storage():
    instance = AsyncMock()
    instance.add = AsyncMock()
    instance.delete = AsyncMock()
    instance.exists = AsyncMock()
    instance.ensure_schema = AsyncMock()

    storage.overwrite(instance)

    return instance


@pytest.mark.asyncio
async def test_rebuild_success(fake_bus, fake_storage):
    fake_bus.topic("person").snapshots = [(42, [{"preferredUsername": "alice"}])]
    await rebuild()
    fake_storage.add.assert_awaited_once_with("alice")


@pytest.mark.asyncio
async def test_rebuild_no_snapshot(fake_bus, fake_storage):
    fake_bus.topic("person").snapshots = []

    await rebuild()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_rebuild_add_failure(fake_bus, fake_storage):
    fake_bus.topic("person").snapshots = [(42, [{"preferredUsername": "alice"}])]
    fake_storage.add.side_effect = RuntimeError("DB error")

    with pytest.raises(RuntimeError, match="DB error"):
        await rebuild()


@pytest.mark.asyncio
async def test_projection_multiple_person(fake_bus, fake_storage):
    fake_bus.topic("person").snapshots = [(10,
                                           [{"preferredUsername": "alice"},
                                            {"preferredUsername": "bob"}])]
    await rebuild()
    assert fake_storage.add.await_count == 2


@pytest.mark.asyncio
async def test_projection_invalid_payload(fake_bus, fake_storage):
    fake_bus.topic("person").snapshots = [(5,
                                           [{"no_username": "alice"}])]
    await rebuild()
    assert fake_storage.add.await_count == 0


@pytest.mark.asyncio
async def test_projection_multiple_person_some_malformed(fake_bus, fake_storage):
    fake_bus.topic("person").snapshots = [(10,
                                           [{"preferredUsername": "alice"},
                                            {"preferredUsername": 43},
                                            {"no_username": "alice"},
                                            {"preferredUsername": "bob"}])]
    await rebuild()
    assert fake_storage.add.await_count == 2

