# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core import message_bus
from profed.components.api.c2s.v1.apps.router import router

 
@pytest.fixture
def client(fake_bus):
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)
 
 
def test_register_app_returns_credentials(client, fake_bus):
    response = client.post("/apps",
                           json={"client_name":   "Tusky",
                                 "redirect_uris": "tusky://callback",
                                 "scopes":        "read write"})
    assert response.status_code == 200
    data = response.json()
    assert "client_id" in data
    assert "client_secret" in data
    assert data["name"] == "Tusky"
    assert data["scopes"] == "read write"
 
 
def test_register_app_publishes_event(client, fake_bus):
    client.post("/apps",
                json={"client_name":   "Tusky",
                      "redirect_uris": "tusky://callback",
                      "scopes":        "read write"})
    published = fake_bus.topic("oauth_apps").published
    assert len(published) == 1
    assert published[0]["event_type"] == "created"
    assert published[0]["object_id"] 
    payload = published[0]["payload"]
    assert payload["client_name"] == "Tusky"
    assert payload["redirect_uris"] == "tusky://callback"
 
 
def test_register_app_default_scopes(client, fake_bus):
    response = client.post("/apps",
                           json={"client_name":   "MinApp",
                                 "redirect_uris": "myapp://cb"})
    assert response.json()["scopes"] == "read"
 
 
def test_register_app_missing_required_fields_returns_422(client):
    response = client.post("/apps", json={"scopes": "read"})
    assert response.status_code == 422


def test_verify_app_credentials_returns_app_info(client):
    response = client.get("/apps/verify_credentials")

    assert response.status_code == 200
    assert response.json()["name"] == "ProFed"


