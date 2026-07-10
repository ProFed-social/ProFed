# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core.config import raw, config
from profed.components.api.s2s.instance_actor import projection
from profed.components.api.s2s.instance_actor.router import router as instance_actor_router


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {"PROFED_PROFED__RUN": "api"}
    config.reset()

    yield

    raw.paths, raw.argv, os.environ = backup


@pytest.fixture
def client(cfg):
    app = FastAPI()
    app.include_router(instance_actor_router)

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset():
    projection._current.clear()
    yield
    projection._current.clear()


def test_actor_document_is_served(client):
    projection._current.update({"public_key_pem": "PEM", "preferredUsername": "example.com",
                                "name": "Example", "summary": "S",
                                "icon": "https://example.com/i.png", "image": None})
    response = client.get("/actor")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/activity+json")
    data = response.json()
    assert data["type"] == "Application"
    assert data["id"] == "https://example.com/actor"
    assert data["publicKey"]["publicKeyPem"] == "PEM"
    assert data["publicKey"]["id"] == "https://example.com/actor#main-key"
    assert data["name"] == "Example"


def test_actor_not_found_without_key(client):
    response = client.get("/actor")

    assert response.status_code == 404

