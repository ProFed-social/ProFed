# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v2.media import router as media_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    media_module.init({})
    app = FastAPI()
    app.include_router(media_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def test_upload_media_returns_422(client):
    assert client.post("/media").status_code == 422


def test_media_active_flag_set_after_init():
    media_module.init({})

    assert media_module.active is True

