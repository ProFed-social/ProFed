# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from profed.core import message_bus, media_storage
from _fakes import FakeMediaStorage, FakeMessageBus


@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()

    yield message_bus._instance

    message_bus._instance = backup


@pytest.fixture
def fake_media_storage():
    backup = media_storage._instance
    media_storage._instance = FakeMediaStorage()

    yield media_storage._instance

    media_storage._instance = backup


@pytest.fixture(autouse=True)
def no_host_cooldown(monkeypatch):
    from profed.http import client
    async def _no_wait(host, interval):
        return 0.0
    monkeypatch.setattr(client, "wait_for", _no_wait)


@pytest.fixture(autouse=True)
def storages_ready_by_default(monkeypatch):
    from profed.core.persistence import base_storage
    original_init = base_storage.BaseStorage.__init__
    def _init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._is_rebuilt = None
    monkeypatch.setattr(base_storage.BaseStorage, "__init__", _init)


