# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v2.suggestions import router as suggestions_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    suggestions_module.init({})
    app = FastAPI()
    app.include_router(suggestions_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def test_get_suggestions_returns_empty_list(client):
    assert client.get("/suggestions").json() == []


def test_suggestions_active_flag_set_after_init():
    suggestions_module.init({})

    assert suggestions_module.active is True

