# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.user_activities import translator


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
def _msg(seq, event_type, object_id, payload):
    return (seq, event_type, object_id, TS, payload)


@pytest.mark.asyncio
async def test_translator_publishes_nothing_on_created(fake_bus):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    await translator.handle_user_events()

    assert fake_bus.topic("activities").published == []



@pytest.mark.asyncio
async def test_translator_publishes_nothing_on_profile_edited(fake_bus):
    fake_bus.topic("users").messages = [
            _msg(1, "profile_edited", "alice", {"name": "A"})]

    await translator.handle_user_events()

    assert fake_bus.topic("activities").published == []


@pytest.mark.asyncio
async def test_translator_publishes_nothing_on_deleted(fake_bus):
    fake_bus.topic("users").messages = [_msg(1, "deleted", "alice", {})]

    await translator.handle_user_events()

    assert fake_bus.topic("activities").published == []

async def test_translator_consumes_all_event_types_without_publishing(fake_bus):
    fake_bus.topic("users").messages = [
            _msg(1, "created",        "alice", {"name": "Alice"}),
            _msg(2, "profile_edited", "alice", {"name": "Alice 2"}),
            _msg(3, "avatar_changed", "alice", {"url": "https://x/a.png"}),
            _msg(4, "keys_generated", "alice",
                 {"public_key_pem": "P", "private_key_pem": "V"}),
            _msg(5, "deleted",        "alice", {})]
    await translator.handle_user_events()
    assert fake_bus.topic("activities").published == []

