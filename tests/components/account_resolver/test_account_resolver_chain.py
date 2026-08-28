# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.account_resolver import resolve


AS2 = "application/activity+json"
LD = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


def _jrd(subject, *hrefs, type_=AS2):
    return {"subject": f"acct:{subject}",
            "links": [{"rel": "self", "type": type_, "href": href} for href in hrefs]}


def _actor(url, username="alice", **extra):
    return {"id": url, "type": "Person", "preferredUsername": username, **extra}


def _run(entry, jrds=None, actors=None):
    known = resolve.Known()
    documents = {"jrd": jrds or {}, "actor": actors or {}}

    while True:
        try:
            return resolve.resolve(entry, known)
        except resolve.NeedsRequest as need:
            known.add(need.kind, need.name, documents[need.kind].get(need.name))


ALICE_URL = "https://a.test/actors/alice"
ALICE_JRD = _jrd("alice@a.test", ALICE_URL)
ALICE = _actor(ALICE_URL)


def test_an_acct_resolves_to_its_actor():
    result = _run("alice@a.test", {"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})

    assert result.acct == "alice@a.test"
    assert result.url == ALICE_URL
    assert result.actor == ALICE
    assert result.acct_aliases == []


def test_a_leading_at_is_stripped():
    assert _run("@alice@a.test", {"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE}).acct == "alice@a.test"


def test_a_failing_webfinger_yields_nothing():
    assert _run("alice@a.test", {}, {}) is None


def test_a_failing_actor_fetch_yields_nothing():
    assert _run("alice@a.test", {"alice@a.test": ALICE_JRD}, {}) is None


def test_a_subject_on_the_same_domain_becomes_canonical():
    jrd = _jrd("christof@a.test", ALICE_URL)
    result = _run("chris@a.test", {"chris@a.test": jrd}, {ALICE_URL: _actor(ALICE_URL, "christof")})

    assert result.acct == "christof@a.test"
    assert result.acct_aliases == ["chris@a.test"]


def test_a_foreign_subject_that_backs_itself_becomes_canonical():
    jrds = {"chris@okunah.de": _jrd("christof@profed.social", "https://profed.social/users/christof"),
            "christof@profed.social": _jrd("christof@profed.social", "https://profed.social/users/christof")}
    actors = {"https://profed.social/users/christof": _actor("https://profed.social/users/christof", "christof")}
    result = _run("chris@okunah.de", jrds, actors)

    assert result.acct == "christof@profed.social"
    assert result.acct_aliases == ["chris@okunah.de"]


def test_a_foreign_subject_that_points_elsewhere_is_discarded():
    jrds = {"alice@a.test": _jrd("victim@victim.test", ALICE_URL),
            "victim@victim.test": _jrd("victim@victim.test", "https://victim.test/actors/victim")}
    result = _run("alice@a.test", jrds, {ALICE_URL: ALICE})

    assert result.acct == "alice@a.test"
    assert result.acct_aliases == []


def test_a_declared_webfinger_handle_wins_when_it_is_backed():
    jrds = {"alice@a.test": ALICE_JRD,
            "chris@okunah.de": _jrd("chris@okunah.de", ALICE_URL)}
    actors = {ALICE_URL: _actor(ALICE_URL, webfinger="acct:chris@okunah.de")}
    result = _run("alice@a.test", jrds, actors)

    assert result.acct == "chris@okunah.de"
    assert result.acct_aliases == ["alice@a.test"]


def test_a_declared_handle_without_backing_is_ignored():
    jrds = {"alice@a.test": ALICE_JRD,
            "chris@okunah.de": _jrd("chris@okunah.de", "https://okunah.de/actors/chris")}
    actors = {ALICE_URL: _actor(ALICE_URL, webfinger="acct:chris@okunah.de")}
    result = _run("alice@a.test", jrds, actors)

    assert result.acct == "alice@a.test"


def test_an_actor_claiming_an_unbacked_handle_keeps_the_asked_one():
    jrds = {"alice@a.test": _jrd("alice@a.test", ALICE_URL)}
    actors = {ALICE_URL: _actor(ALICE_URL, webfinger="acct:victim@victim.test")}
    result = _run("alice@a.test", jrds, actors)

    assert result.acct == "alice@a.test"
    assert result.acct_aliases == []


def test_a_url_whose_handle_is_unbacked_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/actors/other")}
    actors = {ALICE_URL: ALICE}

    assert _run(ALICE_URL, jrds, actors) is None


def test_a_url_resolves_through_the_reverse_lookup():
    result = _run(ALICE_URL, {ALICE_URL: ALICE_JRD, "alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})

    assert result.acct == "alice@a.test"
    assert result.url == ALICE_URL


def test_a_url_falls_back_to_the_actor_when_the_reverse_lookup_fails():
    result = _run(ALICE_URL, {"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})

    assert result.acct == "alice@a.test"


def test_a_reverse_lookup_claiming_a_foreign_domain_is_not_trusted():
    reverse = _jrd("victim@victim.test", ALICE_URL)
    result = _run(ALICE_URL, {ALICE_URL: reverse, "alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})

    assert result.acct == "alice@a.test"


def test_an_actor_id_on_another_host_restarts_the_resolution():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/actors/alice"),
            "alice@real.test": _jrd("alice@real.test", "https://real.test/actors/alice")}
    actors = {"https://a.test/actors/alice": _actor("https://real.test/actors/alice"),
              "https://real.test/actors/alice": _actor("https://real.test/actors/alice")}
    result = _run("alice@a.test", jrds, actors)

    assert result.acct == "alice@real.test"
    assert result.url == "https://real.test/actors/alice"
    assert result.url_aliases == []


def test_following_the_id_within_the_host_records_the_passed_url_as_alias():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/a/alice", "https://a.test/b/alice")}
    actors = {"https://a.test/a/alice": _actor("https://a.test/b/alice"),
              "https://a.test/b/alice": _actor("https://a.test/b/alice")}
    result = _run("alice@a.test", jrds, actors)

    assert result.url == "https://a.test/b/alice"
    assert result.url_aliases == ["https://a.test/a/alice"]


def test_an_id_the_webfinger_does_not_list_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/users/alice")}
    actors = {"https://a.test/users/alice": _actor(ALICE_URL)}

    assert _run("alice@a.test", jrds, actors) is None


def test_a_settled_id_the_webfinger_does_not_list_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/users/alice")}
    actors = {"https://a.test/users/alice": _actor(ALICE_URL),
              ALICE_URL: ALICE}

    assert _run("alice@a.test", jrds, actors) is None


def test_an_id_chain_that_cycles_fails():
    jrds = {"alice@a.test": _jrd("alice@a.test", "https://a.test/a")}
    actors = {"https://a.test/a": _actor("https://a.test/b"),
              "https://a.test/b": _actor("https://a.test/a")}

    assert _run("alice@a.test", jrds, actors) is None


def _requests(entry, jrds=None, actors=None):
    known = resolve.Known()
    documents = {"jrd": jrds or {}, "actor": actors or {}}
    asked = []

    while True:
        try:
            return asked, resolve.resolve(entry, known)
        except resolve.NeedsRequest as need:
            asked.append((need.kind, need.name))
            known.add(need.kind, need.name, documents[need.kind].get(need.name))


def test_the_chain_asks_for_the_webfinger_before_the_actor():
    asked, _ = _requests("alice@a.test", {"alice@a.test": ALICE_JRD}, {ALICE_URL: ALICE})

    assert asked == [("jrd", "alice@a.test"), ("actor", ALICE_URL)]


def test_the_chain_asks_for_nothing_twice():
    asked, _ = _requests("chris@okunah.de",
                         {"chris@okunah.de": _jrd("christof@profed.social", "https://profed.social/users/christof"),
                          "christof@profed.social": _jrd("christof@profed.social",
                                                         "https://profed.social/users/christof")},
                         {"https://profed.social/users/christof": _actor("https://profed.social/users/christof",
                                                                         "christof")})

    assert len(asked) == len(set(asked))


def test_a_resumed_run_needs_no_repeated_request():
    known = resolve.Known()
    known.add("jrd", "alice@a.test", ALICE_JRD)
    known.add("actor", ALICE_URL, ALICE)

    result = resolve.resolve("alice@a.test", known)

    assert result.acct == "alice@a.test"


def test_a_partially_known_run_asks_only_for_what_is_missing():
    known = resolve.Known()
    known.add("jrd", "alice@a.test", ALICE_JRD)

    try:
        resolve.resolve("alice@a.test", known)
        raise AssertionError("expected the actor to be requested")
    except resolve.NeedsRequest as need:
        assert (need.kind, need.name) == ("actor", ALICE_URL)


def test_a_request_that_failed_before_is_not_repeated():
    known = resolve.Known()
    known.add("jrd", "alice@a.test", None)

    assert resolve.resolve("alice@a.test", known) is None

