# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.account_resolver.util import domain_of, host_of


def test_the_domain_follows_the_at():
    assert domain_of("alice@a.test") == "a.test"


def test_a_name_without_a_domain_has_none():
    assert domain_of("alice") == ""


def test_the_last_at_separates_the_domain():
    assert domain_of("alice@old@a.test") == "a.test"


def test_the_host_of_a_url_is_its_netloc():
    assert host_of("https://a.test/actors/alice") == "a.test"


def test_a_port_belongs_to_the_host():
    assert host_of("https://a.test:8443/actors/alice") == "a.test:8443"


def test_a_string_that_is_no_url_has_no_host():
    assert host_of("alice@a.test") == ""

