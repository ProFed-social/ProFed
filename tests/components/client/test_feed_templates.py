# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import mf2py
from profed.components.client.templating import STANDARD_TEMPLATES, build_environment
from profed.components.profile_importer.normalizer import normalize_mf2_to_profile


STATUS = {"id": "1",
          "visibility": "public",
          "content": "<p>Hallo Welt</p>",
          "created_at": "2026-01-01T10:00:00.000Z",
          "url": "https://example.com/@alice/1",
          "uri": "https://example.com/actors/alice/notes/1",
          "reblogs_count": 0,
          "favourites_count": 0,
          "tags": [],
          "account": {"url": "https://example.com/@alice",
                      "acct": "alice",
                      "display_name": "Alice",
                      "username": "alice",
                      "avatar": ""}}

ACCOUNT = {"username": "alice",
           "acct": "alice",
           "display_name": "Alice",
           "url": "https://example.com/@alice",
           "note": "<p>Entwicklerin</p>",
           "avatar": "",
           "header": "",
           "created_at": "2026-01-01T00:00:00.000Z",
           "followers_count": 1,
           "following_count": 2,
           "statuses_count": 3,
           "fields": [],
           "resume": None}


def _block(*parts):
    return {"parts": list(parts), "booster": None, "boosted": [], "cursor": "1"}


def _parse_home(blocks):
    environment = build_environment(STANDARD_TEMPLATES, None)
    return mf2py.parse(doc=environment.get_template("home.html").render(blocks=blocks))


def _feeds(parsed):
    return [item for item in parsed["items"] if "h-feed" in item["type"]]


def test_the_timeline_is_a_top_level_h_feed():
    assert len(_feeds(_parse_home([_block(STATUS)]))) == 1


def test_the_timeline_lists_its_statuses_as_children():
    feed = _feeds(_parse_home([_block(STATUS), _block(STATUS)]))[0]

    assert [child["type"] for child in feed["children"]] == [["h-entry"], ["h-entry"]]


def test_an_empty_timeline_has_no_entries():
    feed = _feeds(_parse_home([]))[0]

    assert feed.get("children", []) == []


def test_the_timeline_entries_keep_their_content():
    feed = _feeds(_parse_home([_block(STATUS)]))[0]

    assert "Hallo Welt" in feed["children"][0]["properties"]["content"][0]["html"]


def test_the_timeline_entries_carry_their_permalink():
    feed = _feeds(_parse_home([_block(STATUS)]))[0]

    assert feed["children"][0]["properties"]["url"] == ["https://example.com/@alice/1"]


def _parse_profile(statuses):
    environment = build_environment(STANDARD_TEMPLATES, None)
    html = environment.get_template("profile.html").render(account=ACCOUNT,
                                                           statuses=statuses,
                                                           handle="alice",
                                                           relationship=None)
    return mf2py.parse(doc=html)


def test_the_profile_feed_is_a_top_level_h_feed():
    assert len(_feeds(_parse_profile([STATUS]))) == 1


def test_the_profile_card_stays_a_top_level_h_card():
    parsed = _parse_profile([STATUS])

    assert any("h-card" in item["type"] for item in parsed["items"])


def test_the_profile_feed_is_not_nested_inside_the_card():
    card = next(item for item in _parse_profile([STATUS])["items"] if "h-card" in item["type"])

    assert not any("h-feed" in child["type"] for child in card.get("children", []))


def test_the_profile_feed_lists_its_statuses_as_children():
    feed = _feeds(_parse_profile([STATUS, STATUS]))[0]

    assert [child["type"] for child in feed["children"]] == [["h-entry"], ["h-entry"]]


def test_the_profile_feed_omits_the_repeated_author():
    feed = _feeds(_parse_profile([STATUS]))[0]

    assert feed["children"][0]["properties"].get("author") is None


def test_the_profile_page_can_be_read_by_the_own_importer():
    assert normalize_mf2_to_profile(_parse_profile([STATUS])) is not None


def _parse_card(fields):
    environment = build_environment(STANDARD_TEMPLATES, None)
    html = environment.get_template("profile.html").render(account=dict(ACCOUNT, fields=fields),
                                                           statuses=[],
                                                           handle="alice",
                                                           relationship=None)
    return html


def test_a_profile_without_fields_shows_no_field_list():
    assert 'class="fields"' not in _parse_card([])


def test_a_field_shows_its_name_and_value():
    html = _parse_card([{"name": "GitHub", "value": "https://github.com/alice", "verified_at": None}])

    assert "GitHub" in html
    assert "https://github.com/alice" in html


def test_a_url_field_becomes_a_rel_me_link():
    html = _parse_card([{"name": "GitHub", "value": "https://github.com/alice", "verified_at": None}])

    assert '<a rel="me" href="https://github.com/alice">' in html


def test_a_plain_text_field_is_not_a_link():
    html = _parse_card([{"name": "Ort", "value": "Hamburg", "verified_at": None}])

    assert "Hamburg" in html
    assert '<a rel="me"' not in html


def test_a_verified_field_is_marked():
    html = _parse_card([{"name": "GitHub", "value": "https://github.com/alice",
                         "verified_at": "2026-08-29T00:00:00.000Z"}])

    assert 'class="field verified"' in html


def test_an_unverified_field_is_not_marked():
    html = _parse_card([{"name": "GitHub", "value": "https://github.com/alice", "verified_at": None}])

    assert "verified" not in html


def test_every_field_gets_its_own_entry():
    html = _parse_card([{"name": "GitHub", "value": "https://github.com/alice", "verified_at": None},
                        {"name": "Site", "value": "https://alice.test/", "verified_at": None}])

    assert html.count('class="field"') == 2


def test_a_gone_field_is_marked():
    html = _parse_card([{"name": "Weg", "value": "https://weg.test/", "verified_at": None, "state": "gone"}])

    assert 'class="field gone"' in html


def test_a_gone_field_keeps_its_rel_me_link():
    html = _parse_card([{"name": "Weg", "value": "https://weg.test/", "verified_at": None, "state": "gone"}])

    assert '<a rel="me" href="https://weg.test/">' in html


def test_an_unverified_field_is_not_marked_as_gone():
    html = _parse_card([{"name": "Da", "value": "https://a.test/", "verified_at": None, "state": "unverified"}])

    assert "gone" not in html


def _card_for(acct, url):
    environment = build_environment(STANDARD_TEMPLATES, None)
    return environment.get_template("profile.html").render(account=dict(ACCOUNT, acct=acct, url=url),
                                                           statuses=[],
                                                           handle=acct,
                                                           relationship=None)


def test_a_remote_profile_links_to_its_origin():
    html = _card_for("bob@r.test", "https://r.test/users/bob")

    assert 'class="origin" href="https://r.test/users/bob"' in html


def test_the_origin_link_names_the_remote_host():
    assert "view on r.test" in _card_for("bob@r.test", "https://r.test/users/bob")


def test_a_local_profile_has_no_origin_link():
    assert 'class="origin"' not in _card_for("alice", "https://example.com/actors/alice")



def _boost_button(status):
    return build_environment(STANDARD_TEMPLATES, None).get_template("boost_button.html").render(status=status)


def test_an_unboosted_status_offers_to_boost():
    html = _boost_button({"id": "42", "reblogs_count": 0, "reblogged": False})

    assert 'hx-post="/statuses/42/reblog"' in html
    assert "is-boosted" not in html


def test_a_boosted_status_offers_to_take_it_back():
    html = _boost_button({"id": "42", "reblogs_count": 1, "reblogged": True})

    assert 'hx-post="/statuses/42/unreblog"' in html
    assert "is-boosted" in html


def test_the_boost_button_shows_the_count():
    assert ">7<" in _boost_button({"id": "42", "reblogs_count": 7, "reblogged": False})

