# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.account_resolver import resolve


AS2 = "application/activity+json"
LD = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


def _jrd(subject="acct:alice@a.test", links=None):
    return {"subject": subject,
            "links": links if links is not None else [{"rel": "self", "type": AS2,
                                                       "href": "https://a.test/actors/alice"}]}


def test_domain_of_takes_the_part_after_the_at():
    assert resolve.domain_of("alice@a.test") == "a.test"


def test_domain_of_a_bare_name_is_empty():
    assert resolve.domain_of("alice") == ""


def test_host_of_takes_the_netloc():
    assert resolve.host_of("https://a.test/actors/alice") == "a.test"


def test_subject_acct_strips_the_scheme():
    assert resolve.subject_acct(_jrd()) == "alice@a.test"


def test_subject_acct_ignores_a_subject_that_is_no_acct():
    assert resolve.subject_acct({"subject": "https://a.test/actors/alice"}) is None


def test_subject_acct_of_an_empty_document_is_none():
    assert resolve.subject_acct({}) is None


def test_declared_acct_comes_from_the_webfinger_attribute():
    assert resolve.declared_acct({"webfinger": "acct:alice@a.test"}) == "alice@a.test"


def test_declared_acct_tolerates_a_leading_at():
    assert resolve.declared_acct({"webfinger": "@alice@a.test"}) == "alice@a.test"


def test_declared_acct_ignores_a_value_without_a_domain():
    assert resolve.declared_acct({"webfinger": "alice"}) is None


def test_declared_acct_of_an_actor_without_the_attribute_is_none():
    assert resolve.declared_acct({"preferredUsername": "alice"}) is None


def test_guessed_acct_combines_username_and_the_host_of_the_id():
    actor = {"preferredUsername": "alice", "id": "https://a.test/actors/alice"}

    assert resolve.guessed_acct(actor) == "alice@a.test"


def test_guessed_acct_without_a_username_is_none():
    assert resolve.guessed_acct({"id": "https://a.test/actors/alice"}) is None


def test_the_declared_acct_wins_over_the_guess():
    actor = {"webfinger": "acct:chris@okunah.de",
             "preferredUsername": "alice",
             "id": "https://a.test/actors/alice"}

    assert resolve.candidate_acct(actor) == "chris@okunah.de"


def test_the_guess_is_used_when_nothing_is_declared():
    actor = {"preferredUsername": "alice", "id": "https://a.test/actors/alice"}

    assert resolve.candidate_acct(actor) == "alice@a.test"


def test_a_document_confirms_a_url_it_lists_as_self():
    assert resolve.confirms(_jrd(), "https://a.test/actors/alice")


def test_a_document_does_not_confirm_a_foreign_url():
    assert not resolve.confirms(_jrd(), "https://evil.test/actors/alice")


def test_the_canonical_url_is_the_only_self_link():
    assert resolve.canonical_url(_jrd()) == "https://a.test/actors/alice"


def test_the_canonical_url_accepts_the_json_ld_type():
    jrd = _jrd(links=[{"rel": "self", "type": LD, "href": "https://a.test/actors/alice"}])

    assert resolve.canonical_url(jrd) == "https://a.test/actors/alice"


def test_the_canonical_url_of_equal_candidates_is_the_smallest():
    jrd = _jrd(links=[{"rel": "self", "type": AS2, "href": "https://a.test/users/christof"},
                      {"rel": "self", "type": AS2, "href": "https://a.test/users/chris"}])

    assert resolve.canonical_url(jrd) == "https://a.test/users/chris"


def test_the_canonical_url_ignores_links_that_are_no_self():
    jrd = _jrd(links=[{"rel": "profile", "type": AS2, "href": "https://a.test/@alice"}])

    assert resolve.canonical_url(jrd) is None


def test_the_canonical_url_of_a_document_without_links_is_none():
    assert resolve.canonical_url({}) is None

