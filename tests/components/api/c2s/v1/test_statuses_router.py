# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core import message_bus
from profed.components.api.c2s.v1.statuses import router as statuses_module
from profed.components.api.c2s.shared.auth import current_user
from profed.models.mastodon import Account
from profed.identity import account_id, actor_url_from_username, heuristic_acct


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client(fake_bus):
    statuses_module.init({"status_max_characters": "5000"})
    app = FastAPI()
    app.include_router(statuses_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


LOCAL_ACCOUNT = Account(id="1",
                        username="alice",
                        acct="alice@example.com",
                        display_name="Alice",
                        url="https://example.com/actors/alice")

NOTE_URL = "https://example.com/act/1"

BOB_URL = "https://remote.example/actors/bob"

CAROL_URL = "https://remote.example/actors/carol"

BOB = Account(id="999", username="bob", acct="bob@remote.example", display_name="Bob", url=BOB_URL)

CAROL = Account(id="777", username="carol", acct="carol@remote.example", display_name="Carol", url=CAROL_URL)

NOTE_STATUS = {"id": "424242",
               "created_at": "2026-01-01T00:00:00+00:00",
               "uri": NOTE_URL,
               "url": NOTE_URL,
               "content": "Hello!",
               "reblog": None,
               "mentions": [],
               "tags": []}

BOOST_STATUS = {"id": "500",
                "created_at": "2026-01-02T00:00:00+00:00",
                "uri": "https://remote.example/carol/announce/1",
                "url": "https://remote.example/carol/announce/1",
                "content": "",
                "reblog": None,
                "mentions": [],
                "tags": []}


def _content_row():
    return {"mastodon_id": 424242,
            "url": NOTE_URL,
            "actor_url": BOB_URL,
            "reblog_of_url": None,
            "status": NOTE_STATUS,
            "content": {"status": NOTE_STATUS, "actor": BOB_URL, "url": NOTE_URL}}


def _boost_row():
    return {"mastodon_id": 500,
            "url": "https://remote.example/carol/announce/1",
            "actor_url": CAROL_URL,
            "reblog_of_url": NOTE_URL,
            "status": BOOST_STATUS,
            "content": {"status": NOTE_STATUS, "actor": BOB_URL, "url": NOTE_URL}}


def _store_returning(row):
    return patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                 AsyncMock(return_value=Mock(get=AsyncMock(return_value=row),
                                             mastodon_ids_for=AsyncMock(return_value={}),
                                             boost_stats=AsyncMock(return_value={}))))


def _patched_accounts(mapping):
    return patch("profed.components.api.c2s.shared.statuses.service.cached_multiple",
                 AsyncMock(return_value=mapping))


def test_create_status_publishes_activity(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        response = client.post("/statuses", json={"status": "Hello Fediverse!"})

    assert response.status_code == 200
    published = fake_bus.topic("raw_activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["activity"]["object"]["type"] == "Note"
    assert published[0]["payload"]["activity"]["object"]["content"] == "Hello Fediverse!"


def test_create_status_returns_status_object(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        response = client.post("/statuses", json={"status": "Hello Fediverse!"})
    data = response.json()

    assert data["content"] == "Hello Fediverse!"
    assert data["visibility"] == "public"
    assert "id" in data
    assert data["account"]["username"] == "alice"


def test_create_status_too_long_returns_422(client, fake_bus):
    response = client.post("/statuses",
                           json={"status": "x" * 5001})

    assert response.status_code == 422


def test_statuses_active_flag_set_after_init():
    statuses_module.init({})
    assert statuses_module.active is True


def test_create_status_activity_has_context_and_to(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        client.post("/statuses", json={"status": "Hello Fediverse!"})

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert activity["@context"] == ["https://www.w3.org/ns/activitystreams"]
    assert activity["to"] == ["https://www.w3.org/ns/activitystreams#Public"]
    assert activity["object"]["to"] == ["https://www.w3.org/ns/activitystreams#Public"]


def test_create_reply_sets_in_reply_to_and_direct_recipients(client, fake_bus):
    root = {"url": "https://remote.example/notes/root"}

    async def by_actor_url(url):
        return {"acct": "bob-canonical@elsewhere.example"} if url == BOB_URL else None

    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         _store_returning(root), \
         patch("profed.components.api.c2s.shared.conversations.storage.storage",
               AsyncMock(return_value=Mock(recipients_for=AsyncMock(return_value=[BOB_URL, CAROL_URL])))), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=Mock(get_by_actor_url=AsyncMock(side_effect=by_actor_url)))):
        response = client.post("/statuses",
                               json={"status": "hi", "in_reply_to_id": "424242", "visibility": "direct"})

    assert response.status_code == 200
    obj = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]
    assert obj["inReplyTo"] == "https://remote.example/notes/root"
    assert obj["to"] == [BOB_URL, CAROL_URL]
    names = {t["href"]: t["name"] for t in obj["tag"]}
    assert names[BOB_URL] == "@bob-canonical@elsewhere.example"
    assert names[CAROL_URL] == "@" + heuristic_acct(CAROL_URL)


def test_create_public_reply_mentions_the_parent_author(client, fake_bus):
    root = {"url": "https://remote.example/notes/root", "actor_url": BOB_URL}

    async def by_actor_url(url):
        return {"acct": "bob-canonical@elsewhere.example"} if url == BOB_URL else None

    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         _store_returning(root), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=Mock(get_by_actor_url=AsyncMock(side_effect=by_actor_url)))):
        response = client.post("/statuses",
                               json={"status": "hi", "in_reply_to_id": "424242", "visibility": "public"})

    assert response.status_code == 200
    obj = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]
    assert obj["inReplyTo"] == "https://remote.example/notes/root"
    assert obj["cc"] == [BOB_URL]
    assert obj["to"] == ["https://www.w3.org/ns/activitystreams#Public"]
    names = {t["href"]: t["name"] for t in obj["tag"]}
    assert names[BOB_URL] == "@bob-canonical@elsewhere.example"


def test_get_status_returns_404(client, fake_bus):
    response = client.get("/statuses/some-id")

    assert response.status_code == 404


def _store_resolving_author(url):
    return patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                 AsyncMock(return_value=Mock(url_for_author=AsyncMock(return_value=url))))


def test_delete_status_publishes_delete_activity_for_the_note_url(client, fake_bus):
    with _store_resolving_author(NOTE_URL):
        response = client.delete("/statuses/424242")

    assert response.status_code == 200
    published = fake_bus.topic("raw_activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Delete"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["activity"]["object"] == NOTE_URL


def test_delete_status_resolves_the_url_for_the_authenticated_author(client, fake_bus):
    store = Mock(url_for_author=AsyncMock(return_value=NOTE_URL))
    with patch("profed.components.api.c2s.shared.statuses.as_objects.storage", AsyncMock(return_value=store)):
        client.delete("/statuses/424242")

    store.url_for_author.assert_awaited_once_with("424242", actor_url_from_username("alice"))


def test_delete_status_returns_404_for_a_foreign_status(client, fake_bus):
    with _store_resolving_author(None):
        response = client.delete("/statuses/500")

    assert response.status_code == 404
    assert fake_bus.topic("raw_activities").published == []


def test_delete_status_returns_404_for_a_non_numeric_id(client, fake_bus):
    store = Mock(url_for_author=AsyncMock(return_value=NOTE_URL))
    with patch("profed.components.api.c2s.shared.statuses.as_objects.storage", AsyncMock(return_value=store)):
        response = client.delete("/statuses/notes-123")

    assert response.status_code == 404
    store.url_for_author.assert_not_awaited()
    assert fake_bus.topic("raw_activities").published == []


def test_status_context_returns_empty_context(client, fake_bus):
    response = client.get("/statuses/some-id/context")

    assert response.status_code == 200
    data = response.json()
    assert data["ancestors"] == []
    assert data["descendants"] == []

def test_status_context_walks_the_discussion_tree_excluding_the_status_itself(client, fake_bus):
    storage = Mock(get=AsyncMock(return_value={"url": "https://r/s"}),
                   discussion_ancestors=AsyncMock(return_value=[{"url": "https://r/root"}]),
                   discussion_of=AsyncMock(return_value=[{"url": "https://r/s"},
                                                         {"url": "https://r/reply"}]))
    make = AsyncMock(return_value=[])
    with patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
               AsyncMock(return_value=storage)), \
         patch("profed.components.api.c2s.shared.statuses.service.make_statuses", make):
        response = client.get("/statuses/42/context")

    assert response.status_code == 200
    storage.discussion_ancestors.assert_awaited_once_with("https://r/s")
    storage.discussion_of.assert_awaited_once_with("https://r/s")
    assert make.await_args_list[1].args[0] == [{"url": "https://r/reply"}]


def test_favourite_returns_404(client, fake_bus):
    response = client.post("/statuses/some-id/favourite")

    assert response.status_code == 404


def test_reblog_returns_404(client, fake_bus):
    response = client.post("/statuses/some-id/reblog")

    assert response.status_code == 404


def test_favourited_by_returns_empty_list(client, fake_bus):
    response = client.get("/statuses/some-id/favourited_by")

    assert response.status_code == 200
    assert response.json() == []


def test_reblogged_by_returns_empty_list(client, fake_bus):
    response = client.get("/statuses/some-id/reblogged_by")

    assert response.status_code == 200
    assert response.json() == []


def test_bookmark_returns_404(client, fake_bus):
    response = client.post("/statuses/note-123/bookmark")

    assert response.status_code == 404


def test_unbookmark_returns_404(client, fake_bus):
    response = client.post("/statuses/note-123/unbookmark")

    assert response.status_code == 404


def test_create_status_sanitises_published_content(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        client.post("/statuses", json={"status": "<p>hi</p><script>steal()</script>"})

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert activity["object"]["content"] == "<p>hi</p>"


def test_create_status_returns_sanitised_content(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        response = client.post("/statuses", json={"status": "<p>hi</p><script>steal()</script>"})


    assert response.json()["content"] == "<p>hi</p>"


def test_create_status_federates_sanitised_spoiler_as_summary(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        client.post("/statuses", json={"status": "hi",
                                       "spoiler_text": "CW <script>x</script>spoiler"})

    obj = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]
    assert obj["summary"] == "CW spoiler"


def test_create_status_without_spoiler_has_no_summary(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        client.post("/statuses", json={"status": "hi"})

    obj = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]
    assert "summary" not in obj


def test_create_status_returns_sanitised_spoiler_text(client, fake_bus):
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        response = client.post("/statuses", json={"status": "hi",
                                                  "spoiler_text": "CW <script>x</script>!"})

    assert response.json()["spoiler_text"] == "CW !"


def test_create_status_does_not_federate_mentions(client, fake_bus):
    store = AsyncMock(get_by_acct=AsyncMock(return_value=None))
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=store)):
        client.post("/statuses", json={"status": "hi @dave@remote.example"})

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert "cc" not in activity
    assert activity["object"]["tag"] == []
    assert activity["object"]["cc"] == []


def test_create_status_response_linkifies_known_mention(client, fake_bus):
    store = AsyncMock(get_by_acct=AsyncMock(return_value={"actor_url": "https://remote.example/actors/dave"}))
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=store)):
        response = client.post("/statuses", json={"status": "hi @dave@remote.example"})

    content = response.json()["content"]
    assert 'href="https://remote.example/actors/dave"' in content
    assert ">@dave</a>" in content


def test_create_status_response_leaves_unknown_mention_plain(client, fake_bus):
    store = AsyncMock(get_by_acct=AsyncMock(return_value=None))
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=store)):
        response = client.post("/statuses", json={"status": "hi @ghost@nowhere.example"})

    assert response.json()["content"] == "hi @ghost@nowhere.example"


def test_create_status_topic_content_stays_unlinked_for_polish(client, fake_bus):
    store = AsyncMock(get_by_acct=AsyncMock(return_value={"actor_url": "https://remote.example/actors/dave"}))
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=store)):
        client.post("/statuses", json={"status": "hi @dave@remote.example"})

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert activity["object"]["content"] == "hi @dave@remote.example"


def test_create_status_response_sets_mentions(client, fake_bus):
    store = AsyncMock(get_by_acct=AsyncMock(return_value={"actor_url": "https://remote.example/actors/dave"}))
    with patch("profed.components.api.c2s.v1.statuses.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)), \
         patch("profed.components.api.c2s.v1.statuses.router._known_accounts_storage",
               AsyncMock(return_value=store)):
        response = client.post("/statuses", json={"status": "hi @dave@remote.example"})
    assert response.json()["mentions"] == [{"id": account_id("dave@remote.example"),
                                            "username": "dave",
                                            "url": "https://remote.example/actors/dave",
                                            "acct": "dave@remote.example"}]

def test_get_status_returns_the_content_status(client):
    with _store_returning(_content_row()), _patched_accounts({BOB_URL: BOB}):
        response = client.get("/statuses/424242")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "424242"
    assert data["content"] == "Hello!"
    assert data["account"]["username"] == "bob"
    assert data["reblog"] is None


def test_get_status_nests_a_boost_as_a_reblog(client):
    with _store_returning(_boost_row()), _patched_accounts({BOB_URL: BOB, CAROL_URL: CAROL}):
        response = client.get("/statuses/500")

    data = response.json()
    assert data["account"]["username"] == "carol"
    assert data["reblog"]["id"] == "424242"
    assert data["reblog"]["account"]["username"] == "bob"


def test_get_status_404_for_an_unknown_id(client):
    with _store_returning(None):
        response = client.get("/statuses/999")

    assert response.status_code == 404


def test_get_status_404_when_the_boost_target_is_unresolvable(client):
    with _store_returning({**_boost_row(), "content": None}):
        response = client.get("/statuses/500")

    assert response.status_code == 404


BOOSTED = {"mastodon_id": 424242,
           "url": "https://remote.example/notes/7",
           "actor_url": "https://remote.example/users/bob",
           "reblog_of_url": None,
           "status": {"id": "424242", "content": "<p>hello</p>"},
           "content": {"status": {"id": "424242", "content": "<p>hello</p>"},
                       "actor": "https://remote.example/users/bob",
                       "url": "https://remote.example/notes/7"}}


def _store_with_boosted(boost_of=None, stats=None):
    return patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
                 AsyncMock(return_value=Mock(get=AsyncMock(return_value=BOOSTED),
                                             mastodon_ids_for=AsyncMock(return_value={}),
                                             boost_of=AsyncMock(return_value=boost_of),
                                             boost_stats=AsyncMock(return_value=stats or {}))))


def _reblog(client):
    with _store_with_boosted(), patch("profed.components.api.c2s.shared.statuses.service.cached_multiple",
                                      AsyncMock(return_value={})):
        return client.post("/statuses/424242/reblog")


def test_a_reblog_publishes_an_announce(client, fake_bus):
    _reblog(client)

    published = fake_bus.topic("raw_activities").published
    assert [message["event_type"] for message in published] == ["Announce"]


def test_the_announce_points_at_the_boosted_note(client, fake_bus):
    _reblog(client)

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"] == BOOSTED["content"]["url"]


def test_the_announce_is_public(client, fake_bus):
    _reblog(client)

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert activity["to"] == ["https://www.w3.org/ns/activitystreams#Public"]


def test_the_announce_reaches_the_author_and_the_followers(client, fake_bus):
    _reblog(client)

    activity = fake_bus.topic("raw_activities").published[0]["payload"]["activity"]
    assert set(activity["cc"]) == {f"{actor_url_from_username('alice')}/followers",
                                   "https://remote.example/users/bob"}


BOOST_STATS = {"https://remote.example/notes/7": {"n_of_boosts": 4, "reblogged": True}}


def _announce_url():
    return f"{actor_url_from_username('alice')}#announce/7"


def _unreblog(client, boost_of):
    with _store_with_boosted(boost_of=boost_of), \
         patch("profed.components.api.c2s.shared.statuses.service.cached_multiple", AsyncMock(return_value={})):
        return client.post("/statuses/424242/unreblog")


def test_an_unreblog_undoes_the_announce(client, fake_bus):
    _unreblog(client, _announce_url())

    published = fake_bus.topic("raw_activities").published
    assert [message["event_type"] for message in published] == ["Undo"]
    assert published[0]["payload"]["activity"]["object"]["type"] == "Announce"


def test_a_reblog_of_an_unknown_status_is_not_found(client, fake_bus):
    store = Mock(get=AsyncMock(return_value=None))
    with patch("profed.components.api.c2s.shared.statuses.as_objects.storage", AsyncMock(return_value=store)):
        response = client.post("/statuses/999/reblog")

    assert response.status_code == 404
    assert fake_bus.topic("raw_activities").published == []


def test_a_reblog_reports_the_status_as_boosted(client, fake_bus):
    assert _reblog(client).json()["reblogged"] is True


def test_a_reblog_raises_the_count(client, fake_bus):
    assert _reblog(client).json()["reblogs_count"] == 1


def test_an_unreblog_reports_the_status_as_not_boosted(client, fake_bus):
    with _store_with_boosted(), patch("profed.components.api.c2s.shared.statuses.service.cached_multiple",
                                      AsyncMock(return_value={})):
        response = client.post("/statuses/424242/unreblog")

    assert response.json()["reblogged"] is False


def test_the_count_never_drops_below_zero(client, fake_bus):
    assert _unreblog(client, None).json()["reblogs_count"] == 0


def test_a_reblog_of_an_already_boosted_status_publishes_nothing(client, fake_bus):
    with _store_with_boosted(boost_of=_announce_url()), \
         patch("profed.components.api.c2s.shared.statuses.service.cached_multiple", AsyncMock(return_value={})):
        client.post("/statuses/424242/reblog")

    assert fake_bus.topic("raw_activities").published == []


def test_a_reblog_of_an_already_boosted_status_does_not_raise_the_count(client, fake_bus):
    with _store_with_boosted(boost_of=_announce_url(), stats=BOOST_STATS), \
         patch("profed.components.api.c2s.shared.statuses.service.cached_multiple", AsyncMock(return_value={})):
        response = client.post("/statuses/424242/reblog")

    assert response.json()["reblogs_count"] == 4


def test_the_undo_carries_the_original_announce_id(client, fake_bus):
    _unreblog(client, _announce_url())

    assert fake_bus.topic("raw_activities").published[0]["payload"]["activity"]["object"]["id"] == _announce_url()


def test_an_unreblog_without_a_recorded_boost_publishes_nothing(client, fake_bus):
    _unreblog(client, None)

    assert fake_bus.topic("raw_activities").published == []


def test_an_unreblog_lowers_the_recorded_count(client, fake_bus):
    with _store_with_boosted(boost_of=_announce_url(), stats=BOOST_STATS), \
         patch("profed.components.api.c2s.shared.statuses.service.cached_multiple", AsyncMock(return_value={})):
             response = client.post("/statuses/424242/unreblog")

    assert response.json()["reblogs_count"] == 3


