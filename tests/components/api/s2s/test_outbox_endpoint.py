# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from profed.core.config import raw, config
from profed.components.api.s2s.outbox.models import OrderedCollection
from profed.components.api.s2s.outbox.router import router as outbox_router
from profed.components.api.s2s.outbox.service import NotVisible


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {
        "PROFED_EXAMPLE__DOMAIN": "example.com",
        "PROFED_PROFED__RUN": "api",
    }

    config.reset()
    yield
    raw.paths, raw.argv, os.environ = backup


@pytest.fixture
def client(cfg):
    app = FastAPI()
    app.include_router(outbox_router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fake_resolve_outbox(monkeypatch):
    fake = AsyncMock()

    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_outbox", fake)

    return fake


def test_outbox_success(client, fake_resolve_outbox):
    fake_resolve_outbox.return_value = OrderedCollection(id="https://example.com/actors/alice/outbox",
                                                         totalItems=0,
                                                         orderedItems=[])

    response = client.get("/actors/alice/outbox")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/activity+json")


def test_outbox_internal_error(client, fake_resolve_outbox):
    fake_resolve_outbox.side_effect = RuntimeError("boom")

    response = client.get("/actors/alice/outbox")

    assert response.status_code == 500


@pytest.fixture
def fake_resolve_note(monkeypatch):
    fake = AsyncMock()

    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_note", fake)

    return fake


def test_note_success(client, fake_resolve_note):
    fake_resolve_note.return_value = {"@context": ["https://www.w3.org/ns/activitystreams"],
                                      "id": "https://example.com/actors/alice/notes/abc",
                                      "type": "Note",
                                      "content": "hi"}

    response = client.get("/actors/alice/notes/abc")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/activity+json")


def test_note_not_found(client, fake_resolve_note):
    fake_resolve_note.return_value = None

    response = client.get("/actors/alice/notes/abc")

    assert response.status_code == 404


def test_note_gone_serves_the_tombstone(client, fake_resolve_note):
    fake_resolve_note.return_value = {"@context": "https://www.w3.org/ns/activitystreams",
                                      "id": "https://example.com/actors/alice/notes/abc",
                                      "type": "Tombstone",
                                      "deleted": "2026-08-24T10:00:00+00:00"}

    response = client.get("/actors/alice/notes/abc")

    assert response.status_code == 410
    assert response.headers["content-type"].startswith("application/activity+json")
    assert response.json()["type"] == "Tombstone"
    assert response.json()["deleted"] == "2026-08-24T10:00:00+00:00"


def test_the_signer_of_the_request_decides_what_the_outbox_shows(client, fake_resolve_outbox, monkeypatch):
    signer = {"actor_url": "https://r.example/actor", "actor_type": "Application"}
    fake_resolve_outbox.return_value = OrderedCollection(id="https://example.com/actors/alice/outbox",
                                                         totalItems=0,
                                                         orderedItems=[])
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.signer_of",
                        AsyncMock(return_value=signer))

    client.get("/actors/alice/outbox")

    assert fake_resolve_outbox.await_args.args[1] == signer


def test_the_signature_is_checked_against_the_path_that_was_asked_for(client, fake_resolve_outbox, monkeypatch):
    checked = AsyncMock(return_value=None)
    fake_resolve_outbox.return_value = OrderedCollection(id="https://example.com/actors/alice/outbox",
                                                         totalItems=0,
                                                         orderedItems=[])
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.signer_of", checked)

    client.get("/actors/alice/outbox")

    assert checked.await_args.args[0] == "GET"
    assert checked.await_args.args[1] == "/actors/alice/outbox"


def test_a_note_the_signer_may_not_see_is_refused(client, monkeypatch):
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.signer_of", AsyncMock(return_value=None))
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_note",
                        AsyncMock(side_effect=NotVisible("https://example.com/actors/alice/notes/abc")))

    assert client.get("/actors/alice/notes/abc").status_code == 401


def test_reactions_of_a_note_the_signer_may_not_see_are_refused(client, monkeypatch):
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.signer_of", AsyncMock(return_value=None))
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_note",
                        AsyncMock(side_effect=NotVisible("https://example.com/actors/alice/notes/abc")))

    assert client.get("/actors/alice/notes/abc/likes").status_code == 401


def test_a_note_that_does_not_exist_is_still_missing(client, monkeypatch):
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.signer_of", AsyncMock(return_value=None))
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_note", AsyncMock(return_value=None))

    assert client.get("/actors/alice/notes/abc").status_code == 404


def _public_note():
    return {"id": "https://example.com/actors/alice/notes/abc",
            "type": "Note",
            "content": "hi",
            "to": ["https://www.w3.org/ns/activitystreams#Public"]}


def _directed_note():
    return {"id": "https://example.com/actors/alice/notes/abc",
            "type": "Note",
            "content": "hi",
            "to": ["https://r.example/users/bob"]}


def _serving(monkeypatch, note):
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.signer_of", AsyncMock(return_value=None))
    monkeypatch.setattr("profed.components.api.s2s.outbox.router.resolve_note", AsyncMock(return_value=note))


def test_a_note_carries_an_etag(client, monkeypatch):
    _serving(monkeypatch, _public_note())

    assert client.get("/actors/alice/notes/abc").headers["etag"].startswith('"')


def test_a_known_etag_is_answered_with_not_modified(client, monkeypatch):
    _serving(monkeypatch, _public_note())
    etag = client.get("/actors/alice/notes/abc").headers["etag"]

    repeated = client.get("/actors/alice/notes/abc", headers={"If-None-Match": etag})

    assert repeated.status_code == 304
    assert repeated.content == b""


def test_another_etag_is_answered_in_full(client, monkeypatch):
    _serving(monkeypatch, _public_note())

    answer = client.get("/actors/alice/notes/abc", headers={"If-None-Match": '"something-else"'})

    assert answer.status_code == 200


def test_a_public_note_may_be_cached_by_anyone(client, monkeypatch):
    _serving(monkeypatch, _public_note())

    assert "public" in client.get("/actors/alice/notes/abc").headers["cache-control"]


def test_a_directed_note_may_only_be_cached_by_its_reader(client, monkeypatch):
    _serving(monkeypatch, _directed_note())

    assert "private" in client.get("/actors/alice/notes/abc").headers["cache-control"]


def test_an_answer_varies_with_the_signature(client, monkeypatch):
    _serving(monkeypatch, _public_note())

    assert client.get("/actors/alice/notes/abc").headers["vary"] == "Signature"


def test_a_note_with_other_content_has_another_etag(client, monkeypatch):
    _serving(monkeypatch, _public_note())
    first = client.get("/actors/alice/notes/abc").headers["etag"]
    _serving(monkeypatch, {**_public_note(), "content": "different"})

    assert client.get("/actors/alice/notes/abc").headers["etag"] != first

