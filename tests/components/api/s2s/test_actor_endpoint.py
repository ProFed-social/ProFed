# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
import pytest
from profed.core.config import raw, config
from profed.components.api.s2s.actor import storage

from profed.components.api.s2s.actor.router import router as actor_router

@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = Mock()
    storage._instance.add = AsyncMock()
    storage._instance.update = AsyncMock()
    storage._instance.delete = AsyncMock()
    storage._instance.fetch = AsyncMock()

    yield storage._instance

    storage._instance = backup


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {"PROFED_EXAMPLE__DOMAIN": "example.com", "PROFED_PROFED__RUN": "api"}

    config.reset()

    yield

    raw.paths, raw.argv, os.environ = backup


@pytest.fixture
def client(cfg):
    app = FastAPI()
    app.include_router(actor_router)

    return TestClient(app)


def test_actor_success(client, fake_storage):
    fake_storage.fetch.return_value = {
        "username": "alice",
        "name": "Alice"
    }
    response = client.get("/actors/alice")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/activity+json")
    data = response.json()
    assert data["name"] == "Alice"
    assert data["preferredUsername"] == "alice"
    assert data["type"] == "Person"
    assert data["id"] == "https://example.com/actors/alice"


def test_actor_not_found(client, fake_storage):
    fake_storage.fetch.return_value = None
    response = client.get("/actors/alice")
    assert response.status_code == 404


def test_actor_internal_error(client, fake_storage):
    fake_storage.fetch.side_effect = RuntimeError()
    response = client.get("/actors/alice")
    assert response.status_code == 500

