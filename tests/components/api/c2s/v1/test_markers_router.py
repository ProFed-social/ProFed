# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.markers import router as markers_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    markers_module.init({})
    app = FastAPI()
    app.include_router(markers_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def test_get_markers_returns_empty_dict(client):
    response = client.get("/markers")

    assert response.status_code == 200
    assert response.json() == {}


def test_get_markers_accepts_timeline_param(client):
    response = client.get("/markers?timeline[]=home&timeline[]=notifications")

    assert response.status_code == 200
    assert response.json() == {}


def test_save_markers_returns_empty_dict(client):
    response = client.post("/markers")

    assert response.status_code == 200
    assert response.json() == {}


def test_markers_active_flag_set_after_init():
    markers_module.init({})

    assert markers_module.active is True

