# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.me_links.extract import link_urls
from profed.components.me_links.remote_actors import profile_url_of


def _actor(*values):
    return {"attachment": [{"type": "PropertyValue", "name": f"n{n}", "value": value}
                           for n, value in enumerate(values)]}


def test_an_actor_without_attachment_has_no_links():
    assert link_urls({}) == []


def test_a_property_value_with_a_url_is_a_link():
    assert link_urls(_actor("https://a.test/x")) == ["https://a.test/x"]


def test_a_http_url_is_a_link_as_well():
    assert link_urls(_actor("http://a.test/x")) == ["http://a.test/x"]


def test_a_value_without_a_scheme_is_no_link():
    assert link_urls(_actor("Hamburg")) == []


def test_every_url_becomes_its_own_link():
    assert link_urls(_actor("https://a.test/x", "https://b.test/y")) == ["https://a.test/x", "https://b.test/y"]


def test_a_non_property_value_attachment_is_ignored():
    actor = {"attachment": [{"type": "Image", "name": "pic", "value": "https://a.test/pic.png"}]}

    assert link_urls(actor) == []


def test_the_profile_url_comes_from_the_actor():
    assert profile_url_of({"url": "https://r.test/@bob"}, "https://r.test/users/bob") == "https://r.test/@bob"


def test_without_a_profile_url_the_actor_url_is_used():
    assert profile_url_of({}, "https://r.test/users/bob") == "https://r.test/users/bob"


def test_a_nonsense_profile_url_is_not_used():
    assert profile_url_of({"url": {"href": "x"}}, "https://r.test/users/bob") == "https://r.test/users/bob"

