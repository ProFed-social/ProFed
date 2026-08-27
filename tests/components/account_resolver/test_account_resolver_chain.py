# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.account_resolver import resolve


AS2 = "application/activity+json"
LD = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


def _jrd(subject, *hrefs, type_=AS2):
    return {"subject": f"acct:{subject}",
            "links": [{"rel": "self", "type": type_, "href": href} for href in hrefs]}


def _actor(url, username="alice", **extra):
    return {"id": url, "type": "Person", "preferredUsername": username, **extra}


def _world(jrds=None, actors=None):
    return (patch.object(resolve, "fetch_jrd", AsyncMock(side_effect=lambda n, s=None: (jrds or {}).get(n))),
            patch.object(resolve, "fetch_actor", AsyncMock(side_effect=lambda u, s=None: (actors or {}).get(u))))


ALICE_URL = "https://a.test/actors/alice"
ALICE_JRD = _jrd("alice@a.test", ALICE_URL)
ALICE = _actor(ALICE_URL)


@pytest.mark.asyncio
async def test_an_acct_resolves_to_its_actor():
    jrd_mock, actor_mock = _world({"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.acct == "alice@a.test"
    assert result.url == ALICE_URL
    assert result.actor == ALICE
    assert result.acct_aliases == []


@pytest.mark.asyncio
async def test_a_leading_at_is_stripped():
    jrd_mock, actor_mock = _world({"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})
    with jrd_mock, actor_mock:
        assert (await resolve.resolve("@alice@a.test")).acct == "alice@a.test"


@pytest.mark.asyncio
async def test_a_failing_webfinger_yields_nothing():
    jrd_mock, actor_mock = _world({}, {})
    with jrd_mock, actor_mock:
        assert await resolve.resolve("alice@a.test") is None


@pytest.mark.asyncio
async def test_a_failing_actor_fetch_yields_nothing():
    jrd_mock, actor_mock = _world({"alice@a.test": ALICE_JRD}, {})
    with jrd_mock, actor_mock:
        assert await resolve.resolve("alice@a.test") is None


@pytest.mark.asyncio
async def test_a_subject_on_the_same_domain_becomes_canonical():
    jrd = _jrd("christof@a.test", ALICE_URL)
    jrd_mock, actor_mock = _world({"chris@a.test": jrd}, {ALICE_URL: _actor(ALICE_URL, "christof")})
    with jrd_mock, actor_mock:
        result = await resolve.resolve("chris@a.test")

    assert result.acct == "christof@a.test"
    assert result.acct_aliases == ["chris@a.test"]


@pytest.mark.asyncio
async def test_a_foreign_subject_that_backs_itself_becomes_canonical():
    jrds = {"chris@okunah.de": _jrd("christof@profed.social", "https://profed.social/users/christof"),
            "christof@profed.social": _jrd("christof@profed.social", "https://profed.social/users/christof")}
    actors = {"https://profed.social/users/christof": _actor("https://profed.social/users/christof", "christof")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        result = await resolve.resolve("chris@okunah.de")

    assert result.acct == "christof@profed.social"
    assert result.acct_aliases == ["chris@okunah.de"]


@pytest.mark.asyncio
async def test_a_foreign_subject_that_points_elsewhere_is_discarded():
    jrds = {"alice@a.test": _jrd("victim@victim.test", ALICE_URL),
            "victim@victim.test": _jrd("victim@victim.test", "https://victim.test/actors/victim")}
    jrd_mock, actor_mock = _world(jrds, {ALICE_URL: ALICE})
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.acct == "alice@a.test"
    assert result.acct_aliases == []


@pytest.mark.asyncio
async def test_a_declared_webfinger_handle_wins_when_it_is_backed():
    jrds = {"alice@a.test": ALICE_JRD,
            "chris@okunah.de": _jrd("chris@okunah.de", ALICE_URL)}
    actors = {ALICE_URL: _actor(ALICE_URL, webfinger="acct:chris@okunah.de")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.acct == "chris@okunah.de"
    assert result.acct_aliases == ["alice@a.test"]


@pytest.mark.asyncio
async def test_a_declared_handle_without_backing_is_ignored():
    jrds = {"alice@a.test": ALICE_JRD,
            "chris@okunah.de": _jrd("chris@okunah.de", "https://okunah.de/actors/chris")}
    actors = {ALICE_URL: _actor(ALICE_URL, webfinger="acct:chris@okunah.de")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.acct == "alice@a.test"


@pytest.mark.asyncio
async def test_an_actor_claiming_an_unbacked_handle_keeps_the_asked_one():
    jrds = {"alice@a.test": _jrd("alice@a.test", ALICE_URL)}
    actors = {ALICE_URL: _actor(ALICE_URL, webfinger="acct:victim@victim.test")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.acct == "alice@a.test"
    assert result.acct_aliases == []


@pytest.mark.asyncio
async def test_a_url_whose_handle_is_unbacked_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/actors/other")}
    actors = {ALICE_URL: ALICE}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        assert await resolve.resolve(ALICE_URL) is None


@pytest.mark.asyncio
async def test_a_url_resolves_through_the_reverse_lookup():
    jrd_mock, actor_mock = _world({ALICE_URL: ALICE_JRD, "alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})
    with jrd_mock, actor_mock:
        result = await resolve.resolve(ALICE_URL)

    assert result.acct == "alice@a.test"
    assert result.url == ALICE_URL


@pytest.mark.asyncio
async def test_a_url_falls_back_to_the_actor_when_the_reverse_lookup_fails():
    jrd_mock, actor_mock = _world({"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})
    with jrd_mock, actor_mock:
        result = await resolve.resolve(ALICE_URL)

    assert result.acct == "alice@a.test"


@pytest.mark.asyncio
async def test_a_reverse_lookup_claiming_a_foreign_domain_is_not_trusted():
    reverse = _jrd("victim@victim.test", ALICE_URL)
    jrd_mock, actor_mock = _world({ALICE_URL: reverse, "alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})
    with jrd_mock, actor_mock:
        result = await resolve.resolve(ALICE_URL)

    assert result.acct == "alice@a.test"


@pytest.mark.asyncio
async def test_an_actor_id_on_another_host_restarts_the_resolution():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/actors/alice"),
            "alice@real.test": _jrd("alice@real.test", "https://real.test/actors/alice")}
    actors = {"https://a.test/actors/alice": _actor("https://real.test/actors/alice"),
              "https://real.test/actors/alice": _actor("https://real.test/actors/alice")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.acct == "alice@real.test"
    assert result.url == "https://real.test/actors/alice"
    assert result.url_aliases == []


@pytest.mark.asyncio
async def test_following_the_id_within_the_host_records_the_passed_url_as_alias():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/a/alice", "https://a.test/b/alice")}
    actors = {"https://a.test/a/alice": _actor("https://a.test/b/alice"),
              "https://a.test/b/alice": _actor("https://a.test/b/alice")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        result = await resolve.resolve("alice@a.test")

    assert result.url == "https://a.test/b/alice"
    assert result.url_aliases == ["https://a.test/a/alice"]


@pytest.mark.asyncio
async def test_an_id_the_webfinger_does_not_list_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/users/alice")}
    actors = {"https://a.test/users/alice": _actor(ALICE_URL)}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        assert await resolve.resolve("alice@a.test") is None


@pytest.mark.asyncio
async def test_a_settled_id_the_webfinger_does_not_list_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/users/alice")}
    actors = {"https://a.test/users/alice": _actor(ALICE_URL),
              ALICE_URL: ALICE}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        assert await resolve.resolve("alice@a.test") is None


@pytest.mark.asyncio
async def test_an_id_chain_that_cycles_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/a")}
    actors = {"https://a.test/a": _actor("https://a.test/b"),
              "https://a.test/b": _actor("https://a.test/a")}
    jrd_mock, actor_mock = _world(jrds, actors)
    with jrd_mock, actor_mock:
        assert await resolve.resolve("alice@a.test") is None

