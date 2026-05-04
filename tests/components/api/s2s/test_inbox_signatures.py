# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from profed.http.signatures import (generate_key_pair, key_id_from_signature_header,
                                     sign_request, verify_request)
from profed.components.api.s2s.inbox.router import router as inbox_router


def test_key_id_from_signature_header_extracts_actor_url():
    header = 'keyId="https://remote.example/users/bob#main-key",algorithm="rsa-sha256"'
    assert key_id_from_signature_header(header) == "https://remote.example/users/bob"


def test_key_id_from_signature_header_without_fragment():
    header = 'keyId="https://remote.example/users/bob",algorithm="rsa-sha256"'
    assert key_id_from_signature_header(header) == "https://remote.example/users/bob"


def test_key_id_from_signature_header_missing_returns_none():
    assert key_id_from_signature_header('algorithm="rsa-sha256"') is None


def test_verify_request_accepts_valid_signature():
    public_pem, private_pem = generate_key_pair()
    body    = b'{"type":"Follow"}'

    headers = sign_request("POST",
                            "https://local.example/actors/alice/inbox",
                            body,
                            "https://remote.example/users/bob#main-key",
                            private_pem)

    assert verify_request("POST", "/actors/alice/inbox", headers, body, public_pem) is True


def test_verify_request_rejects_tampered_body():
    public_pem, private_pem = generate_key_pair()
    body    = b'{"type":"Follow"}'

    headers = sign_request("POST", "https://local.example/actors/alice/inbox",
                            body, "https://remote.example/users/bob#main-key", private_pem)

    assert verify_request("POST", "/actors/alice/inbox", headers,
                           b'{"type":"Undo"}', public_pem) is False


def test_verify_request_rejects_wrong_key():
    _, private_pem  = generate_key_pair()
    other_public, _ = generate_key_pair()
    body    = b'{"type":"Follow"}'
    headers = sign_request("POST", "https://local.example/actors/alice/inbox",
                            body, "https://remote.example/users/bob#main-key", private_pem)

    assert verify_request("POST", "/actors/alice/inbox", headers, body, other_public) is False


def test_verify_request_rejects_missing_signature_header():
    public_pem, _ = generate_key_pair()

    assert verify_request("POST", "/actors/alice/inbox", {"host": "local.example"},
                           b'{"type":"Follow"}', public_pem) is False


@pytest.fixture
def client_with_mocks(monkeypatch):
    fake_accept = AsyncMock(return_value=True)
    monkeypatch.setattr("profed.components.api.s2s.inbox.router.accept_inbox_activity",
                        fake_accept)

    app = FastAPI()
    app.include_router(inbox_router)

    return TestClient(app, raise_server_exceptions=False), fake_accept


def test_inbox_rejects_unsigned_request(client_with_mocks):
    client, _ = client_with_mocks

    with patch("profed.components.api.s2s.inbox.router.verify_inbox_request", AsyncMock(return_value=False)):
        response = client.post("/actors/alice/inbox",
                               json={"type": "Follow", "actor": "https://remote.example/users/bob"})

    assert response.status_code == 401


def test_inbox_accepts_correctly_signed_request(client_with_mocks):
    client, _ = client_with_mocks

    with patch("profed.components.api.s2s.inbox.router.verify_inbox_request", AsyncMock(return_value=True)):
        response = client.post("/actors/alice/inbox",
                               json={"type": "Follow", "actor": "https://remote.example/users/bob"})

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_verify_inbox_request_uses_projection_key():
    public_pem, private_pem = generate_key_pair()
    body    = b'{"type":"Follow"}'
    headers = sign_request("POST", "https://local.example/actors/alice/inbox",
                            body, "https://remote.example/users/bob#main-key", private_pem)
    mock_storage = AsyncMock()
    mock_storage.get_by_actor_url = AsyncMock(return_value={"public_key_pem": public_pem})

    with patch("profed.components.api.s2s.inbox.service.public_keys_storage", AsyncMock(return_value=mock_storage)):
        from profed.components.api.s2s.inbox.service import verify_inbox_request
        result = await verify_inbox_request("POST", "/actors/alice/inbox", headers, body)

    assert result is True


@pytest.mark.asyncio
async def test_verify_inbox_request_fetches_key_when_not_in_projection():
    public_pem, private_pem = generate_key_pair()
    body    = b'{"type":"Follow"}'
    headers = sign_request("POST", "https://local.example/actors/alice/inbox",
                            body, "https://remote.example/users/bob#main-key", private_pem)
    mock_storage = AsyncMock()
    mock_storage.get_by_actor_url = AsyncMock(return_value=None)

    with patch("profed.components.api.s2s.inbox.service.public_keys_storage", AsyncMock(return_value=mock_storage)), \
         patch("profed.components.api.s2s.inbox.service.fetch_and_register_actor", AsyncMock(return_value=public_pem)):
        from profed.components.api.s2s.inbox.service import verify_inbox_request
        result = await verify_inbox_request("POST", "/actors/alice/inbox", headers, body)

    assert result is True


@pytest.mark.asyncio
async def test_verify_inbox_request_retries_with_fresh_key_on_stale_projection():
    public_pem, private_pem = generate_key_pair()
    old_public_pem, _ = generate_key_pair()
    body    = b'{"type":"Follow"}'
    headers = sign_request("POST", "https://local.example/actors/alice/inbox",
                            body, "https://remote.example/users/bob#main-key", private_pem)
    mock_storage = AsyncMock()
    mock_storage.get_by_actor_url = AsyncMock(return_value={"public_key_pem": old_public_pem})

    with patch("profed.components.api.s2s.inbox.service.public_keys_storage", AsyncMock(return_value=mock_storage)), \
         patch("profed.components.api.s2s.inbox.service.fetch_and_register_actor", AsyncMock(return_value=public_pem)):
        from profed.components.api.s2s.inbox.service import verify_inbox_request
        result = await verify_inbox_request("POST", "/actors/alice/inbox", headers, body)

    assert result is True


@pytest.mark.asyncio
async def test_verify_inbox_request_rejects_when_no_key_available():
    _, private_pem = generate_key_pair()
    body    = b'{"type":"Follow"}'
    headers = sign_request("POST", "https://local.example/actors/alice/inbox",
                            body, "https://remote.example/users/bob#main-key", private_pem)
    mock_storage = AsyncMock()
    mock_storage.get_by_actor_url = AsyncMock(return_value=None)

    with patch("profed.components.api.s2s.inbox.service.public_keys_storage", AsyncMock(return_value=mock_storage)), \
         patch("profed.components.api.s2s.inbox.service.fetch_and_register_actor", AsyncMock(return_value=None)):
        from profed.components.api.s2s.inbox.service import verify_inbox_request
        result = await verify_inbox_request("POST", "/actors/alice/inbox", headers, body)

    assert result is False

