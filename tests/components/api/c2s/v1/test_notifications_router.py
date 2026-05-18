# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.notifications import router as notifications_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    notifications_module.init({})
    app = FastAPI()
    app.include_router(notifications_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def test_list_notifications_returns_empty_list(client):
    response = client.get("/notifications")

    assert response.status_code == 200
    assert response.json() == []


def test_list_notifications_accepts_query_params(client):
    response = client.get("/notifications?limit=5&types=follow&exclude_types=mention")

    assert response.status_code == 200
    assert response.json() == []


def test_clear_notifications_returns_empty_object(client):
    response = client.post("/notifications/clear")

    assert response.status_code == 200
    assert response.json() == {}


def test_dismiss_notification_returns_empty_object(client):
    response = client.post("/notifications/abc123/dismiss")

    assert response.status_code == 200
    assert response.json() == {}


def test_notifications_active_flag_set_after_init():
    notifications_module.init({})

    assert notifications_module.active is True

