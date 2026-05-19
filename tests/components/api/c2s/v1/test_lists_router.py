# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.lists import router as lists_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    lists_module.init({})
    app = FastAPI()
    app.include_router(lists_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS

    return TestClient(app)


def test_get_lists_returns_empty_list(client):
    assert client.get("/lists").json() == []


def test_get_bookmarks_returns_empty_list(client):
    assert client.get("/bookmarks").json() == []


def test_get_favourites_returns_empty_list(client):
    assert client.get("/favourites").json() == []


def test_lists_active_flag_set_after_init():
    lists_module.init({})

    assert lists_module.active is True

