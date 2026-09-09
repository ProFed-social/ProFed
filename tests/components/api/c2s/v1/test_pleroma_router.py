# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from starlette.routing import Match
from fastapi.testclient import TestClient
from profed import identity
from profed.identity import actor_url_from_username
from profed.models.mastodon import Status, placeholder_account
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.v1 import pleroma as pleroma_module


@pytest.fixture(autouse=True)
def domain():
    with patch.object(identity, "domain", lambda: "example.com"):
        yield


CLAIMS = {"preferred_username": "alice", "sub": "alice"}

BOOSTED = {"mastodon_id": 424242,
           "url": "https://remote.example/notes/7",
           "actor_url": "https://remote.example/users/bob",
           "kind": "content",
           "status": {"id": "424242", "content": "<p>hello</p>"},
           "content": {"status": {"id": "424242", "content": "<p>hello</p>"},
                       "actor": "https://remote.example/users/bob",
                       "url": "https://remote.example/notes/7",
                       "mastodon_id": "424242"}}


@pytest.fixture
def client(fake_bus):
    app = FastAPI()
    app.include_router(pleroma_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


def _status_with(reactions):
    return Status(id="424242",
                  uri=BOOSTED["content"]["url"],
                  created_at="2026-01-01T00:00:00.000Z",
                  account=placeholder_account(BOOSTED["content"]["actor"]),
                  content="<p>hello</p>",
                  favourites_count=sum(entry["count"] for entry in reactions),
                  favourited=any(entry["me"] for entry in reactions),
                  pleroma={"emoji_reactions": reactions})


def _like_url():
    return f"{actor_url_from_username('alice')}#like/7"


def _store(reaction_of=None):
    return patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                 AsyncMock(return_value=Mock(get=AsyncMock(return_value=BOOSTED),
                                             mastodon_ids_for=AsyncMock(return_value={}),
                                             own_reaction=AsyncMock(return_value=reaction_of),
                                             boost_stats=AsyncMock(return_value={}),
                                             reaction_stats=AsyncMock(return_value={}),
                                             reaction_breakdown=AsyncMock(return_value={}))))


def _own(emoji):
    return {"reaction_url": _like_url(), "emoji": emoji}


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
    _react(client, "🎉", reaction_of=_own("🎉"))

    assert fake_bus.topic("raw_activities").published == []


def test_a_reaction_reports_the_status_as_favourited(client, fake_bus):
    assert _react(client, "🎉").json()["favourited"] is True


def test_removing_a_reaction_undoes_the_recorded_like(client, fake_bus):
    _unreact(client, "🎉", reaction_of=_own("🎉"))

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]["id"] == _like_url()


def test_removing_a_reaction_ignores_the_emoji_in_the_path(client, fake_bus):
    _unreact(client, "🐶", reaction_of=_own("🎉"))

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]["id"] == _like_url()


def test_removing_a_reaction_that_is_not_recorded_publishes_nothing(client, fake_bus):
    _unreact(client, "🎉", reaction_of=None)

    assert fake_bus.topic("raw_activities").published == []


def test_removing_a_reaction_reports_the_status_as_not_favourited(client, fake_bus):
    assert _unreact(client, "🎉", reaction_of=_own("🎉")).json()["favourited"] is False


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


def test_a_reaction_shows_the_chosen_emoji_before_the_projection_catches_up(client, fake_bus):
    reactions = _react(client, "🎉").json()["pleroma"]["emoji_reactions"]

    assert reactions == [{"name": "🎉", "count": 1, "me": True}]


def test_a_reaction_joins_an_existing_bucket(client, fake_bus):
    with patch("profed.components.api.c2s.shared.statuses.service.make_statuses",
               AsyncMock(return_value=[_status_with([{"name": "🎉", "count": 2, "me": False}])])):
        reactions = _react(client, "🎉").json()["pleroma"]["emoji_reactions"]

    assert reactions == [{"name": "🎉", "count": 3, "me": True}]


def test_removing_a_reaction_takes_the_emoji_away_again(client, fake_bus):
    with patch("profed.components.api.c2s.shared.statuses.service.make_statuses",
               AsyncMock(return_value=[_status_with([{"name": "🎉", "count": 1, "me": True}])])):
        reactions = _unreact(client, "🎉", reaction_of=_own("🎉")).json()["pleroma"]["emoji_reactions"]

    assert reactions == []


def test_removing_a_reaction_leaves_the_reactions_of_others(client, fake_bus):
    with patch("profed.components.api.c2s.shared.statuses.service.make_statuses",
               AsyncMock(return_value=[_status_with([{"name": "🎉", "count": 2, "me": True},
                                                     {"name": "🐶", "count": 1, "me": False}])])):
        reactions = _unreact(client, "🎉", reaction_of=_own("🎉")).json()["pleroma"]["emoji_reactions"]

    assert reactions == [{"name": "🎉", "count": 1, "me": False}, {"name": "🐶", "count": 1, "me": False}]


def test_the_undo_is_addressed_to_the_author(client, fake_bus):
    _unreact(client, "🎉", reaction_of=_own("🎉"))

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["to"] == [BOOSTED["content"]["actor"]]


def test_choosing_another_emoji_undoes_the_old_reaction_and_sets_the_new_one(client, fake_bus):
    _react(client, "🐶", reaction_of=_own("🎉"))

    published = fake_bus.topic("raw_activities").published
    assert [message["event_type"] for message in published] == ["Undo", "Like"]
    assert published[0]["payload"]["activity"]["object"]["id"] == _like_url()
    assert published[1]["payload"]["activity"]["content"] == "🐶"


def test_choosing_another_emoji_replaces_it_in_the_breakdown(client, fake_bus):
    with patch("profed.components.api.c2s.shared.statuses.service.make_statuses",
               AsyncMock(return_value=[_status_with([{"name": "🎉", "count": 1, "me": True}])])):
        reactions = _react(client, "🐶", reaction_of=_own("🎉")).json()["pleroma"]["emoji_reactions"]

    assert reactions == [{"name": "🐶", "count": 1, "me": True}]


