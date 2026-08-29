# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.profile_importer.normalizer import rel_me_fields


def _mf2(me, texts=None):
    return {"rels": {"me": me},
            "rel-urls": {url: {"text": (texts or {}).get(url, ""), "rels": ["me"]} for url in me}}


def test_a_page_without_rel_me_has_no_fields():
    assert rel_me_fields({"rels": {}, "rel-urls": {}}) == []


def test_a_rel_me_link_becomes_a_field():
    fields = rel_me_fields(_mf2(["https://github.com/chris"], {"https://github.com/chris": "GitHub"}))

    assert fields == [{"name": "GitHub", "value": "https://github.com/chris"}]


def test_the_link_text_names_the_field():
    fields = rel_me_fields(_mf2(["https://example.org/x"], {"https://example.org/x": "  My Site  "}))

    assert fields[0]["name"] == "My Site"


def test_without_a_link_text_the_host_names_the_field():
    fields = rel_me_fields(_mf2(["https://okunah.de/"]))

    assert fields[0]["name"] == "okunah.de"


def test_every_rel_me_link_becomes_its_own_field():
    fields = rel_me_fields(_mf2(["https://a.test/x", "https://b.test/y"]))

    assert [field["value"] for field in fields] == ["https://a.test/x", "https://b.test/y"]


def test_the_order_of_the_page_is_kept():
    fields = rel_me_fields(_mf2(["https://b.test/y", "https://a.test/x"]))

    assert [field["value"] for field in fields] == ["https://b.test/y", "https://a.test/x"]


def test_a_link_without_rel_urls_entry_still_becomes_a_field():
    fields = rel_me_fields({"rels": {"me": ["https://a.test/x"]}, "rel-urls": {}})

    assert fields == [{"name": "a.test", "value": "https://a.test/x"}]

