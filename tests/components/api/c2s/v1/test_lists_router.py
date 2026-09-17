# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed import identity
from profed.components.api.c2s.v1.lists import router as lists_module
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture(autouse=True)
def domain():
    with patch.object(identity, "domain", lambda: "example.com"):
        yield


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


def _marks(**methods):
    return patch("profed.components.api.c2s.shared.bookmarks.storage.storage",
                 AsyncMock(return_value=Mock(**methods)))


def test_a_cursor_reaches_the_storage_as_a_number(client):
    page = AsyncMock(return_value=[])

    with _marks(page=page):
        client.get("/bookmarks?max_id=400&since_id=100&limit=7")

    page.assert_awaited_once_with("https://example.com/actors/alice", 7, 400, 100)


def test_a_cursor_that_is_no_number_is_refused(client):
    with _marks(page=AsyncMock(return_value=[])):
        assert client.get("/bookmarks?max_id=gestern").status_code == 422


def test_lists_active_flag_set_after_init():
    lists_module.init({})

    assert lists_module.active is True


def test_get_filters_returns_empty_list(client):
    assert client.get("/filters").json() == []

