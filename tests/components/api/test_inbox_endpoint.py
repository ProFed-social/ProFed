# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from profed.components.api.routers.inbox import router as inbox_router


@pytest.fixture
def fake_accept_inbox_activity(monkeypatch):
    fake = AsyncMock()

    monkeypatch.setattr("profed.components.api.routers.inbox.accept_inbox_activity",
                        fake)

    return fake


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(inbox_router)
    return TestClient(app)


def test_inbox_accepts_valid_activity(client, fake_accept_inbox_activity):
    fake_accept_inbox_activity.return_value = True

    response = client.post("/actors/alice/inbox",
                           json={"type": "Follow",
                                 "actor": "https://remote.example/actors/bob"})

    assert response.status_code == 202


def test_inbox_returns_404_for_unknown_actor(client, fake_accept_inbox_activity):
    fake_accept_inbox_activity.return_value = False

    response = client.post("/actors/alice/inbox",
                           json={"type": "Follow",
                                 "actor": "https://remote.example/actors/bob"})

    assert response.status_code == 404


def test_inbox_returns_400_for_malformed_activity(client, fake_accept_inbox_activity):
    fake_accept_inbox_activity.side_effect = ValueError("Malformed ActivityPub activity")

    response = client.post("/actors/alice/inbox",
                           json={"actor": "https://remote.example/actors/bob"})

    assert response.status_code == 400


def test_inbox_returns_500_on_internal_error(client, fake_accept_inbox_activity):
    fake_accept_inbox_activity.side_effect = RuntimeError("boom")

    response = client.post("/actors/alice/inbox",
                           json={"type": "Follow",
                                 "actor": "https://remote.example/actors/bob"})

    assert response.status_code == 500


def test_inbox_invalid_username(client):
    response = client.post("/actors/alice@example.com/inbox",
                           json={"type": "Follow"})

    assert response.status_code == 422
