# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.shared.known_servers import projection
from profed.components.api.c2s.shared.known_servers import storage as storage_module


AT = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self):
        self.observations = {}
        self.updates = {}

    async def record_observation(self, host, observed_at):
        self.observations[host] = observed_at

    async def record_update(self, host, software, features, checked_at):
        self.updates[host] = {"software": software, "features": features, "checked_at": checked_at}


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_an_observed_emoji_react_is_recorded(fake_storage):
    await projection._observed("a.test", {"activity_type": "EmojiReact", "observed_at": AT.isoformat()})

    assert fake_storage.observations == {"a.test": AT}


@pytest.mark.asyncio
async def test_an_observed_like_says_nothing_about_reactions(fake_storage):
    await projection._observed("a.test", {"activity_type": "Like", "observed_at": AT.isoformat()})

    assert fake_storage.observations == {}


@pytest.mark.asyncio
async def test_an_update_is_recorded(fake_storage):
    await projection._updated("a.test", {"checked_at": AT.isoformat(),
                                         "software": "pleroma",
                                         "features": ["pleroma_emoji_reactions"]})

    assert fake_storage.updates["a.test"] == {"software": "pleroma",
                                              "features": ["pleroma_emoji_reactions"],
                                              "checked_at": AT}


@pytest.mark.asyncio
async def test_an_update_without_features_records_an_empty_list(fake_storage):
    await projection._updated("a.test", {"checked_at": AT.isoformat(), "software": None, "features": None})

    assert fake_storage.updates["a.test"]["features"] == []

