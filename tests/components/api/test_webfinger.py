# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api import storage
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.routers.well_known import router as webfinger_router
from profed.components.api.services.webfinger import resolve_actor_url


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = Mock()
    storage._instance.add = AsyncMock()
    storage._instance.update = AsyncMock()
    storage._instance.delete = AsyncMock()
    storage._instance.fetch_actor_url = AsyncMock()

    yield storage._instance

    storage._instance = backup


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(webfinger_router)

    return TestClient(app)


def test_webfinger_endpoint_success(client, fake_storage):
    fake_storage.fetch_actor_url.return_value = "https://example.com/alice"
    response = client.get("/.well-known/webfinger?resource=acct:alice@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "acct:alice@example.com"
    assert data["links"][0]["href"] == "https://example.com/alice"


def test_webfinger_endpoint_not_found(client, fake_storage):
    fake_storage.fetch_actor_url.return_value = None
    response = client.get("/.well-known/webfinger?resource=acct:unknown@example.com")
    assert response.status_code == 404


def test_webfinger_endpoint_storage_error(client, fake_storage):
    fake_storage.fetch_actor_url.side_effect = RuntimeError("DB error")
    response = client.get("/.well-known/webfinger?resource=acct:alice@example.com")
    assert response.status_code == 500


def test_webfinger_invalid_resource(client):
    response = client.get("/.well-known/webfinger?resource=invalid")

    assert response.status_code == 422


def test_webfinger_missing_resource(client):
    response = client.get("/.well-known/webfinger")

    assert response.status_code == 422


def test_webfinger_response_structure(client, fake_storage):
    fake_storage.fetch_actor_url.return_value = "https://example.com/alice"

    response = client.get("/.well-known/webfinger?resource=acct:alice@example.com")

    data = response.json()

    assert "subject" in data
    assert "links" in data
    assert isinstance(data["links"], list)



@pytest.mark.asyncio
async def test_resolve_actor_url_success(fake_storage):
    fake_storage.fetch_actor_url.return_value = "https://example.com/alice"

    result = await resolve_actor_url("alice@example.com")

    assert result == "https://example.com/alice"


@pytest.mark.asyncio
async def test_resolve_actor_url_storage_error(fake_storage):
    fake_storage.fetch_actor_url.side_effect = RuntimeError()

    with pytest.raises(RuntimeError):
        await resolve_actor_url("alice@example.com")

