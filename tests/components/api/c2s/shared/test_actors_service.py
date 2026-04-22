# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.shared.actors import storage
from profed.components.api.c2s.shared.actors.service import resolve_actor
 
 
@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = Mock()
    storage._instance.fetch = AsyncMock()
    yield storage._instance
    storage._instance = backup
 
 
@pytest.mark.asyncio
async def test_resolve_actor_found(fake_storage):
    fake_storage.fetch.return_value = {"name": "Alice", "username": "alice"}
    actor = await resolve_actor("alice")
    assert actor is not None
    assert actor.name == "Alice"
 
 
@pytest.mark.asyncio
async def test_resolve_actor_not_found(fake_storage):
    fake_storage.fetch.return_value = None
    actor = await resolve_actor("unknown")
    assert actor is None

