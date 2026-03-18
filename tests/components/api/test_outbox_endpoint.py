# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from profed.core.config import raw, config
from profed.components.api.routers.outbox import router as outbox_router


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {
        "PROFED_EXAMPLE__DOMAIN": "example.com",
        "PROFED_PROFED__RUN": "api",
    }

    config.reset()
    yield
    raw.paths, raw.argv, os.environ = backup


@pytest.fixture
def client(cfg):
    app = FastAPI()
    app.include_router(outbox_router)
    return TestClient(app)


@pytest.fixture
def fake_resolve_outbox(monkeypatch):
    fake = AsyncMock()

    monkeypatch.setattr(
        "profed.components.api.routers.outbox.resolve_outbox",
        fake,
    )

    return fake


def test_outbox_success(client, fake_resolve_outbox):
    fake_resolve_outbox.return_value = {
        "@context": ["https://www.w3.org/ns/activitystreams"],
        "id": "https://example.com/actors/alice/outbox",
        "type": "OrderedCollection",
        "totalItems": 0,
        "orderedItems": [],
    }

    response = client.get("/actors/alice/outbox")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/activity+json")


def test_outbox_internal_error(client, fake_resolve_outbox):
    fake_resolve_outbox.side_effect = RuntimeError("boom")

    response = client.get("/actors/alice/outbox")

    assert response.status_code == 500

