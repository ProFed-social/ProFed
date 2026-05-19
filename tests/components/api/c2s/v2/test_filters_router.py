# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v2.filters import router as filters_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    filters_module.init({})
    app = FastAPI()
    app.include_router(filters_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def test_get_filters_returns_empty_list(client):
    assert client.get("/filters").json() == []


def test_filters_active_flag_set_after_init():
    filters_module.init({})

    assert filters_module.active is True

