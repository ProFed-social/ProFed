# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.s2s.webfinger import storage
from fastapi import FastAPI
from fastapi.testclient import TestClient

from profed.core.config import raw, config
from profed.components.api.s2s.webfinger.router import router as webfinger_router
from profed.components.api.s2s.webfinger.service import resolve_actor_url, resolve_acct_from_actor_url


@pytest.fixture
def fake_storage():
    instance = Mock()
    instance.add = AsyncMock()
    instance.delete = AsyncMock()
    instance.exists = AsyncMock()

    storage.overwrite(instance)

    return instance

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
    app.include_router(webfinger_router)

    return TestClient(app)


def test_webfinger_endpoint_success(client, fake_storage):
    fake_storage.exists.return_value = True
    response = client.get("/.well-known/webfinger?resource=acct:alice@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "acct:alice@example.com"
    assert data["links"][0]["href"] == "https://example.com/actors/alice"


def test_webfinger_endpoint_not_found(client, fake_storage):
    fake_storage.exists.return_value = False
    response = client.get("/.well-known/webfinger?resource=acct:unknown@example.com")
    assert response.status_code == 404


def test_webfinger_endpoint_storage_error(client, fake_storage):
    fake_storage.exists.side_effect = RuntimeError("DB error")
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
    fake_storage.exists.return_value = True

    result = await resolve_actor_url("alice@example.com")

    assert result == "https://example.com/actors/alice"


@pytest.mark.asyncio
async def test_resolve_actor_url_storage_error(fake_storage):
    fake_storage.exists.side_effect = RuntimeError()

    with pytest.raises(RuntimeError):
        await resolve_actor_url("alice@example.com")


def test_webfinger_actor_url_success(client, fake_storage, cfg):
    fake_storage.exists.return_value = True
    response = client.get("/.well-known/webfinger"
                          "?resource=https://example.com/actors/alice")
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "acct:alice@example.com"
    assert data["links"][0]["href"] == "https://example.com/actors/alice"
 
 
def test_webfinger_actor_url_wrong_domain(client, fake_storage, cfg):
    response = client.get("/.well-known/webfinger"
                          "?resource=https://other.example.com/actors/alice")
    assert response.status_code == 404
 
 
def test_webfinger_actor_url_not_found(client, fake_storage, cfg):
    fake_storage.exists.return_value = False
    response = client.get("/.well-known/webfinger"
                          "?resource=https://example.com/actors/unknown")
    assert response.status_code == 404
 
 
def test_webfinger_actor_url_wrong_path(client, fake_storage, cfg):
    response = client.get("/.well-known/webfinger"
                          "?resource=https://example.com/users/alice")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_resolve_acct_from_actor_url_success(fake_storage, cfg):
    fake_storage.exists.return_value = True
    result = await resolve_acct_from_actor_url("https://example.com/actors/alice")
    assert result == "alice@example.com"
 
 
@pytest.mark.asyncio
async def test_resolve_acct_from_actor_url_wrong_domain(fake_storage, cfg):
    result = await resolve_acct_from_actor_url("https://other.example.com/actors/alice")
    assert result is None
 
 
@pytest.mark.asyncio
async def test_resolve_acct_from_actor_url_not_found(fake_storage, cfg):
    fake_storage.exists.return_value = False
    result = await resolve_acct_from_actor_url("https://example.com/actors/unknown")
    assert result is None
 
 
@pytest.mark.asyncio
async def test_resolve_acct_from_actor_url_wrong_path(fake_storage, cfg):
    result = await resolve_acct_from_actor_url("https://example.com/users/alice")
    assert result is None

