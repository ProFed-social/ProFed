# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from unittest.mock import patch

from profed import identity
from profed.http import client
from profed.core import message_bus, media_storage
from profed.core.config import config, raw
from profed.core.persistence import base_storage
from profed.components.api.c2s.shared.bookmarks import storage as bookmarks_storage
from _fakes import FakeMediaStorage, FakeMessageBus


class _NobodyBookmarkedAnything:
    async def marked(self, object_urls, actor_url):
        return set()

    async def page(self, actor_url, limit, max_id, since_id):
        return []


@pytest.fixture(autouse=True)
def domain():
    with patch.object(identity, "domain", lambda: "example.com"):
        yield


@pytest.fixture(autouse=True)
def no_bookmarks():
    backup = bookmarks_storage._instance
    bookmarks_storage._instance = _NobodyBookmarkedAnything()

    yield bookmarks_storage._instance

    bookmarks_storage._instance = backup


@pytest.fixture
def api_config():
    raw.paths = []
    raw.argv = ["", "--profed.run=api", "--api.domain=example.com"]
    os.environ = {key: value
                  for key, value in os.environ.items()
                  if not key.startswith("PROFED_")}
    config.reset()

    return config()


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
    async def _no_wait(host, interval):
        return 0.0
    monkeypatch.setattr(client, "wait_for", _no_wait)


@pytest.fixture(autouse=True)
def storages_ready_by_default(monkeypatch):
    original_init = base_storage.BaseStorage.__init__

    def _init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._is_rebuilt = None
    monkeypatch.setattr(base_storage.BaseStorage, "__init__", _init)

