# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from profed.core.config import raw, config
from profed.components.api.s2s.outbox.router import router as outbox_router


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {"PROFED_EXAMPLE__DOMAIN": "example.com", "PROFED_PROFED__RUN": "api"}

    config.reset()
    yield
    raw.paths, raw.argv, os.environ = backup


@pytest.fixture
def client(cfg):
    app = FastAPI()
    app.include_router(outbox_router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fake_note(monkeypatch):
    fake = AsyncMock(return_value={"id": "x", "type": "Note"})
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_note", fake)
    return fake


@pytest.fixture
def fake_resolve(monkeypatch, fake_note):
    fake = AsyncMock(return_value={"id": "x", "type": "OrderedCollection"})
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_reactions", fake)
    return fake


def test_the_likes_collection_is_served(client, fake_resolve):
    response = client.get("/actors/alice/notes/7/likes")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/activity+json")


def test_the_emoji_reactions_collection_is_served(client, fake_resolve):
    assert client.get("/actors/alice/notes/7/emojiReactions").status_code == 200
    assert fake_resolve.await_args.args[2] == "emojiReactions"


def test_another_name_is_not_a_collection(client, fake_resolve):
    assert client.get("/actors/alice/notes/7/replies").status_code == 404
    assert fake_resolve.await_count == 0


def test_a_missing_note_answers_with_not_found(client, fake_resolve, fake_note):
    fake_note.return_value = None

    assert client.get("/actors/alice/notes/7/likes").status_code == 404
    assert fake_resolve.await_count == 0


def test_a_deleted_note_answers_with_not_found(client, fake_resolve, fake_note):
    fake_note.return_value = {"id": "x", "type": "Tombstone"}

    assert client.get("/actors/alice/notes/7/likes").status_code == 404
    assert fake_resolve.await_count == 0


def test_the_page_flag_is_passed_on(client, fake_resolve):
    client.get("/actors/alice/notes/7/likes?page=true")

    assert fake_resolve.await_args.args[3] is True


def test_the_before_marker_is_passed_on(client, fake_resolve):
    client.get("/actors/alice/notes/7/likes?page=true&before=4711")

    assert fake_resolve.await_args.args[4] == 4711


def test_a_nonsense_marker_is_rejected(client, fake_resolve):
    assert client.get("/actors/alice/notes/7/likes?before=soon").status_code == 422

