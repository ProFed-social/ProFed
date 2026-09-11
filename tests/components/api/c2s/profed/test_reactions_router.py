# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Match
from profed import identity
from profed.components.api.c2s import profed
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.profed.reactions import router as reactions_module


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture(autouse=True)
def domain():
    with patch.object(identity, "domain", lambda: "example.com"):
        yield


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(reactions_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def _store(counts=None, last=None):
    return patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                 AsyncMock(return_value=Mock(
                     reaction_counts_of=AsyncMock(return_value=counts if counts is not None else []),
                     last_toned_reaction_of=AsyncMock(return_value=last))))


def test_the_history_reports_the_counts_and_the_last_toned_emoji(client):
    with _store(counts=[{"emoji": "🎉", "n_of_uses": 3}], last="👍🏽"):
        body = client.get("/reactions/history").json()

    assert body == {"counts": [{"emoji": "🎉", "n_of_uses": 3}], "last_toned": "👍🏽"}


def test_a_reader_without_reactions_gets_an_empty_history(client):
    with _store():
        body = client.get("/reactions/history").json()
    assert body == {"counts": [], "last_toned": None}


def test_the_history_asks_for_the_reader(client):
    with _store() as storage:
        client.get("/reactions/history")

    store = storage.return_value
    store.reaction_counts_of.assert_awaited_once_with("https://example.com/actors/alice")


def _handles(deactivate, path):
    reactions_module.init({})
    app = FastAPI()
    profed.mount_routers(app, deactivate)
    scope = {"type": "http", "method": "GET", "path": path, "path_params": {}, "root_path": "", "headers": []}
    return any(route.matches(scope)[0] != Match.NONE for route in app.routes)


def test_the_history_is_mounted_under_the_profed_prefix():
    assert _handles([], "/profed/reactions/history") is True


def test_the_history_can_be_deactivated():
    assert _handles(["reactions"], "/profed/reactions/history") is False

