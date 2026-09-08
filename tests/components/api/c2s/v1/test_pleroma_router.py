# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from starlette.routing import Match
from fastapi.testclient import TestClient
from profed.identity import actor_url_from_username
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.v1 import pleroma as pleroma_module


CLAIMS = {"preferred_username": "alice", "sub": "alice"}

BOOSTED = {"mastodon_id": 424242,
           "url": "https://remote.example/notes/7",
           "actor_url": "https://remote.example/users/bob",
           "kind": "content",
           "status": {"id": "424242", "content": "<p>hello</p>"},
           "content": {"status": {"id": "424242", "content": "<p>hello</p>"},
                       "actor": "https://remote.example/users/bob",
                       "url": "https://remote.example/notes/7"}}


@pytest.fixture
def client(fake_bus):
    app = FastAPI()
    app.include_router(pleroma_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def _like_url():
    return f"{actor_url_from_username('alice')}#like/7"


def _store(reaction_of=None):
    return patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                 AsyncMock(return_value=Mock(get=AsyncMock(return_value=BOOSTED),
                                             mastodon_ids_for=AsyncMock(return_value={}),
                                             reaction_of=AsyncMock(return_value=reaction_of),
                                             boost_stats=AsyncMock(return_value={}),
                                             reaction_stats=AsyncMock(return_value={}),
                                             reaction_breakdown=AsyncMock(return_value={}))))


def _react(client, emoji, reaction_of=None):
    with _store(reaction_of), \
         patch("profed.components.api.c2s.shared.statuses.service.cached_multiple", AsyncMock(return_value={})):
        return client.put(f"/pleroma/statuses/424242/reactions/{emoji}")


def _unreact(client, emoji, reaction_of):
    with _store(reaction_of), \
         patch("profed.components.api.c2s.shared.statuses.service.cached_multiple", AsyncMock(return_value={})):
        return client.delete(f"/pleroma/statuses/424242/reactions/{emoji}")


def test_a_reaction_publishes_a_like_carrying_the_emoji(client, fake_bus):
    _react(client, "🎉")

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert activity["content"] == "🎉"
    assert activity["_misskey_reaction"] == "🎉"


def test_a_reaction_is_published_as_a_like_addressed_to_the_author(client, fake_bus):
    _react(client, "🎉")

    published = fake_bus.topic("raw_activities").published
    assert [message["event_type"] for message in published] == ["Like"]
    assert published[0]["payload"]["activity"]["to"] == [BOOSTED["content"]["actor"]]


def test_a_second_reaction_publishes_nothing(client, fake_bus):
    _react(client, "🎉", reaction_of=_like_url())

    assert fake_bus.topic("raw_activities").published == []


def test_a_reaction_reports_the_status_as_favourited(client, fake_bus):
    assert _react(client, "🎉").json()["favourited"] is True


def test_removing_a_reaction_undoes_the_recorded_like(client, fake_bus):
    _unreact(client, "🎉", reaction_of=_like_url())

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]["id"] == _like_url()


def test_removing_a_reaction_ignores_the_emoji_in_the_path(client, fake_bus):
    _unreact(client, "🐶", reaction_of=_like_url())

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]["id"] == _like_url()


def test_removing_a_reaction_that_is_not_recorded_publishes_nothing(client, fake_bus):
    _unreact(client, "🎉", reaction_of=None)

    assert fake_bus.topic("raw_activities").published == []


def test_removing_a_reaction_reports_the_status_as_not_favourited(client, fake_bus):
    assert _unreact(client, "🎉", reaction_of=_like_url()).json()["favourited"] is False


def _handles(deactivate, method, path):
    from profed.components.api.c2s import v1

    pleroma_module.init({})
    app = FastAPI()
    v1.mount_routers(app, deactivate)
    scope = {"type": "http", "method": method, "path": path, "path_params": {}, "root_path": "", "headers": []}
    return any(route.matches(scope)[0] != Match.NONE for route in app.routes)


def test_the_reaction_routes_are_mounted_under_the_api():
    assert _handles([], "PUT", "/v1/pleroma/statuses/42/reactions/x") is True
    assert _handles([], "DELETE", "/v1/pleroma/statuses/42/reactions/x") is True


def test_the_reaction_routes_can_be_deactivated():
    assert _handles(["pleroma"], "PUT", "/v1/pleroma/statuses/42/reactions/x") is False

