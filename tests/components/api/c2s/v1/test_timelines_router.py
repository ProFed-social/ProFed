# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.models.mastodon import Account
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.timelines import router as timelines_module
from profed.components.api.c2s.shared.statuses import user_timeline
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}

NOTE_URL = "https://example.com/act/1"
BOOST_URL = "https://remote.example/carol/announce/1"
BOB_URL = "https://remote.example/actors/bob"
CAROL_URL = "https://remote.example/actors/carol"

STATUS = {"id": "424242",
          "created_at": "2026-01-01T00:00:00+00:00",
          "uri": NOTE_URL,
          "url": NOTE_URL,
          "content": "Hello!",
          "reblog": None,
          "mentions": [],
          "tags": []}

BOOST = {"id": "500",
         "created_at": "2026-01-02T00:00:00+00:00",
         "uri": BOOST_URL,
         "url": BOOST_URL,
         "content": "",
         "reblog": None,
         "mentions": [],
         "tags": []}

BOB = Account(id="999", username="bob", acct="bob@remote.example", display_name="Bob", url=BOB_URL)

CAROL = Account(id="777", username="carol", acct="carol@remote.example", display_name="Carol", url=CAROL_URL)



def _content_row():
    return {"mastodon_id": 424242,
            "url": NOTE_URL,
            "actor_url": BOB_URL,
            "kind": "content",
            "status": STATUS,
            "content": {"status": STATUS, "actor": BOB_URL, "url": NOTE_URL}}


def _boost_row():
    return {"mastodon_id": 500,
            "url": BOOST_URL,
            "actor_url": CAROL_URL,
            "kind": "announce",
            "status": BOOST,
            "content": {"status": STATUS, "actor": BOB_URL, "url": NOTE_URL}}


class FakeStorage:
    def __init__(self, rows):
        self._rows = rows
    async def fetch(self, username, limit=20, max_id=None, since_id=None, max_depth=20):
        return self._rows


def _patched_accounts(mapping):
    return patch("profed.components.api.c2s.shared.statuses.service.cached_multiple",
                 AsyncMock(return_value=mapping))


@pytest.fixture(autouse=True)
def no_boosts():
    with patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
               AsyncMock(return_value=AsyncMock(boost_stats=AsyncMock(return_value={})))):
        yield


@pytest.fixture
def client():
    timelines_module.init({})
    backup = user_timeline._instance
    user_timeline._instance = FakeStorage([_content_row()])
    app = FastAPI()
    app.include_router(timelines_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS

    yield TestClient(app)

    user_timeline._instance = backup



def test_home_timeline_returns_the_content_status(client):
    with _patched_accounts({BOB_URL: BOB}):
        response = client.get("/timelines/home")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "424242"
    assert data[0]["content"] == "Hello!"
    assert data[0]["account"]["username"] == "bob"
    assert data[0]["reblog"] is None


def test_home_timeline_nests_a_boost_as_a_reblog(client):
    user_timeline._instance = FakeStorage([_boost_row()])

    with _patched_accounts({BOB_URL: BOB, CAROL_URL: CAROL}):
        response = client.get("/timelines/home")

    data = response.json()
    assert data[0]["account"]["username"] == "carol"
    assert data[0]["reblog"]["id"] == "424242"
    assert data[0]["reblog"]["content"] == "Hello!"
    assert data[0]["reblog"]["account"]["username"] == "bob"


def test_home_timeline_falls_back_to_a_placeholder_account(client):
    with _patched_accounts({}):
        response = client.get("/timelines/home")

    assert response.status_code == 200
    assert response.json()[0]["account"]["username"] == "bob"


def test_home_timeline_does_not_webfinger_on_read(client):
    with _patched_accounts({BOB_URL: BOB}) as cached:
        client.get("/timelines/home")

    cached.assert_awaited_once()


def test_home_timeline_empty(client):
    user_timeline._instance = FakeStorage([])

    with _patched_accounts({}):
        response = client.get("/timelines/home")

    assert response.status_code == 200
    assert response.json() == []


def test_timelines_active_flag_set_after_init():
    timelines_module.init({})
    assert timelines_module.active is True


def test_public_timeline_returns_empty_list(client):
    response = client.get("/timelines/public")

    assert response.status_code == 200
    assert response.json() == []


def test_public_timeline_accepts_local_flag(client):
    response = client.get("/timelines/public?local=true")

    assert response.status_code == 200
    assert response.json() == []


def test_hashtag_timeline_returns_empty_list(client):
    response = client.get("/timelines/tag/python")

    assert response.status_code == 200
    assert response.json() == []

