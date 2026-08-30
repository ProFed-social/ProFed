# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.shared.me_links import projection
from profed.components.api.c2s.shared.me_links import storage as storage_module


CHECKED = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)

EDGE = "https://p.test/@alice|https://a.test/"


class FakeStorage:
    def __init__(self):
        self.rows = {}

    async def upsert(self, profile_url, link_url, state, checked_at):
        self.rows[(profile_url, link_url)] = {"state": state, "checked_at": checked_at}

    async def delete(self, profile_url, link_url):
        self.rows.pop((profile_url, link_url), None)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_a_verified_event_is_stored(fake_bus, fake_storage):
    await projection._checked("verified")(EDGE, {"checked_at": CHECKED.isoformat()})

    assert fake_storage.rows[("https://p.test/@alice", "https://a.test/")]["state"] == "verified"


@pytest.mark.asyncio
async def test_an_unverified_event_is_stored(fake_bus, fake_storage):
    await projection._checked("unverified")(EDGE, {"checked_at": CHECKED.isoformat()})

    assert fake_storage.rows[("https://p.test/@alice", "https://a.test/")]["state"] == "unverified"


@pytest.mark.asyncio
async def test_a_gone_event_is_stored(fake_bus, fake_storage):
    await projection._checked("gone")(EDGE, {"checked_at": CHECKED.isoformat()})

    assert fake_storage.rows[("https://p.test/@alice", "https://a.test/")]["state"] == "gone"


@pytest.mark.asyncio
async def test_the_check_time_is_kept(fake_bus, fake_storage):
    await projection._checked("verified")(EDGE, {"checked_at": CHECKED.isoformat()})

    assert fake_storage.rows[("https://p.test/@alice", "https://a.test/")]["checked_at"] == CHECKED


@pytest.mark.asyncio
async def test_a_deleted_event_removes_the_row(fake_bus, fake_storage):
    await projection._checked("verified")(EDGE, {"checked_at": CHECKED.isoformat()})

    await projection._deleted(EDGE, {})

    assert fake_storage.rows == {}


@pytest.mark.asyncio
async def test_deleting_an_unknown_row_is_harmless(fake_bus, fake_storage):
    await projection._deleted(EDGE, {})

    assert fake_storage.rows == {}

