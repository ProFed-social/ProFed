# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import xml.etree.ElementTree as ElementTree

import httpx
import pytest
from fastapi import FastAPI

from profed.components.client import profile, templating
from profed.components.client.templating import rfc822


_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)
_DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"

_ATOM = "{http://www.w3.org/2005/Atom}"
_PROFED_FEDIVERSE = "{https://codeberg.org/ProFed/ns#}fediverse"

def _resp(status_code, **kwargs):
    return httpx.Response(status_code,
                          request=httpx.Request("GET", "https://test.local/api"),
                          **kwargs)


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses

    async def get(self, path, **kwargs):
        for marker, response in self._responses.items():
            if marker in path:
                return response

        return _resp(404)


def _app(monkeypatch, responses):
    monkeypatch.setattr(profile, "api_client", lambda: _FakeClient(responses))
    monkeypatch.setattr(profile, "environment", lambda: _ENV)

    app = FastAPI()
    app.include_router(profile.router)

    return app


def _account():
    return {"id": "1",
            "username": "alice",
            "acct": "alice@example.test",
            "display_name": "Alice",
            "note": "<p>Entwicklerin &amp; Autorin</p>",
            "url": "https://example.test/@alice",
            "avatar": None,
            "header": None,
            "statuses_count": 2,
            "following_count": 5,
            "followers_count": 7,
            "created_at": "2026-01-15T10:00:00+00:00",
            "resume": None}


def _posts():
    return [{"id": "10",
             "content": "<p>Hallo <b>Welt</b></p>",
             "url": "https://example.test/@alice/10",
             "created_at": "2026-02-01T09:00:00+00:00",
             "reblogs_count": 1,
             "favourites_count": 3,
             "tags": [{"name": "python", "url": "https://example.test/tags/python"},
                      {"name": "rss", "url": "https://example.test/tags/rss"}]},
            {"id": "11",
             "content": "<p>Ein deutlich laengerer Beitrag, der mehr Text traegt als in eine "
                        "Titelzeile passt und darum gekuerzt gehoert</p>",
             "url": "https://example.test/@alice/11",
             "created_at": "2026-02-02T09:00:00+00:00",
             "reblogs_count": 0,
             "favourites_count": 0,
             "tags": []}]


async def _fetch(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.get(path)


async def _feed(monkeypatch, posts=None):
    app = _app(monkeypatch, {"lookup": _resp(200, json=_account()),
                             "statuses": _resp(200, json=_posts() if posts is None else posts)})
    return await _fetch(app, "/@alice/feed.xml")


def _channel(body):
    return ElementTree.fromstring(body).find("channel")


async def test_the_feed_is_served_as_rss(monkeypatch):
    response = await _feed(monkeypatch)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")


async def test_the_feed_is_wellformed_rss_2(monkeypatch):
    root = ElementTree.fromstring((await _feed(monkeypatch)).text)

    assert (root.tag, root.get("version")) == ("rss", "2.0")


async def test_the_channel_names_the_account(monkeypatch):
    assert _channel((await _feed(monkeypatch)).text).findtext("title") == "Alice (@alice@example.test)"


async def test_the_channel_description_carries_the_note_without_markup(monkeypatch):
    description = _channel((await _feed(monkeypatch)).text).findtext("description")

    assert description == "Entwicklerin & Autorin"


async def test_every_status_becomes_an_item(monkeypatch):
    assert len(_channel((await _feed(monkeypatch)).text).findall("item")) == 2


async def test_an_item_links_to_the_status(monkeypatch):
    item = _channel((await _feed(monkeypatch)).text).find("item")

    assert item.findtext("link") == "https://example.test/@alice/10"


async def test_an_item_uses_the_permalink_as_guid(monkeypatch):
    guid = _channel((await _feed(monkeypatch)).text).find("item").find("guid")

    assert (guid.text, guid.get("isPermaLink")) == ("https://example.test/@alice/10", "true")


async def test_an_item_dates_itself_in_the_rss_format(monkeypatch):
    item = _channel((await _feed(monkeypatch)).text).find("item")

    assert item.findtext("pubDate") == "Sun, 01 Feb 2026 09:00:00 +0000"


async def test_an_item_keeps_the_content_as_description(monkeypatch):
    item = _channel((await _feed(monkeypatch)).text).find("item")

    assert item.findtext("description") == "<p>Hallo <b>Welt</b></p>"


async def test_an_item_titles_itself_from_the_text(monkeypatch):
    item = _channel((await _feed(monkeypatch)).text).find("item")

    assert item.findtext("title") == "Hallo Welt"


async def test_a_long_text_is_shortened_for_the_title(monkeypatch):
    items = _channel((await _feed(monkeypatch)).text).findall("item")

    assert len(items[1].findtext("title")) < 80


async def test_an_account_without_posts_yields_an_empty_channel(monkeypatch):
    assert _channel((await _feed(monkeypatch, posts=[])).text).findall("item") == []


async def test_dangerous_markup_does_not_reach_the_feed(monkeypatch):
    posts = [{**_posts()[0], "content": "<p>hi</p><script>steal()</script>"}]

    assert "steal()" not in (await _feed(monkeypatch, posts=posts)).text


async def test_the_profile_page_advertises_its_feed(monkeypatch):
    app = _app(monkeypatch, {"lookup": _resp(200, json=_account()),
                             "statuses": _resp(200, json=_posts())})

    body = (await _fetch(app, "/@alice")).text

    assert 'type="application/rss+xml"' in body
    assert 'href="/@alice/feed.xml"' in body


@pytest.mark.parametrize("value", ["", None, "kein Datum"])
def test_an_unusable_timestamp_yields_no_date(value):
    assert rfc822(value) == ""


def test_a_timestamp_without_a_zone_is_still_formatted():
    assert rfc822("2026-01-01T10:00:00").startswith("Thu, 01 Jan 2026 10:00:00")


async def test_the_channel_credits_the_account_as_creator_by_name(monkeypatch):
    assert _channel((await _feed(monkeypatch)).text).findtext(_DC_CREATOR) == "Alice"


async def test_an_account_with_an_avatar_exposes_a_channel_image(monkeypatch):
    account = {**_account(), "avatar": "https://example.test/avatar.png"}
    app = _app(monkeypatch, {"lookup": _resp(200, json=account),
                             "statuses": _resp(200, json=_posts())})

    image = _channel((await _fetch(app, "/@alice/feed.xml")).text).find("image")

    assert image.findtext("url") == "https://example.test/avatar.png"
    assert image.findtext("link") == "https://test.local/@alice"


async def test_an_account_without_an_avatar_has_no_image(monkeypatch):
    assert _channel((await _feed(monkeypatch)).text).find("image") is None


async def test_hashtags_become_item_categories(monkeypatch):
    item = _channel((await _feed(monkeypatch)).text).find("item")

    assert [category.text for category in item.findall("category")] == ["python", "rss"]


async def test_a_category_records_the_tag_url_as_its_domain(monkeypatch):
    item = _channel((await _feed(monkeypatch)).text).find("item")

    assert item.find("category").get("domain") == "https://example.test/tags/python"


async def test_a_status_without_tags_has_no_categories(monkeypatch):
    items = _channel((await _feed(monkeypatch)).text).findall("item")

    assert items[1].findall("category") == []


def _first_author(body):
    return _channel(body).find("item").find(_ATOM + "author")


async def test_an_item_names_its_author(monkeypatch):
    author = _first_author((await _feed(monkeypatch)).text)

    assert author.findtext(_ATOM + "name") == "Alice"


async def test_an_item_author_links_to_the_profile(monkeypatch):
    author = _first_author((await _feed(monkeypatch)).text)

    assert author.findtext(_ATOM + "uri") == "https://example.test/@alice"


async def test_an_item_author_carries_the_fediverse_handle(monkeypatch):
    author = _first_author((await _feed(monkeypatch)).text)

    assert author.findtext(_PROFED_FEDIVERSE) == "@alice@example.test"


async def test_a_boost_is_attributed_to_the_original_author(monkeypatch):
    boost = {**_posts()[0],
             "reblog": {"account": {"display_name": "Bob",
                                    "username": "bob",
                                    "url": "https://remote.test/@bob",
                                    "acct": "bob@remote.test"}}}

    author = _first_author((await _feed(monkeypatch, posts=[boost])).text)

    assert author.findtext(_ATOM + "name") == "Bob"
    assert author.findtext(_PROFED_FEDIVERSE) == "@bob@remote.test"


async def test_the_profile_head_advertises_the_fediverse_creator(monkeypatch):
    app = _app(monkeypatch, {"lookup": _resp(200, json=_account()),
                             "statuses": _resp(200, json=_posts())})

    body = (await _fetch(app, "/@alice")).text

    assert 'name="fediverse:creator"' in body
    assert 'content="@alice@example.test"' in body


def _media_post(media):
    return {**_posts()[0], "media_attachments": media}


async def test_a_media_attachment_becomes_an_enclosure(monkeypatch):
    post = _media_post([{"url": "https://example.test/m/1.jpg",
                         "type": "image",
                         "mime_type": "image/jpeg"}])

    item = _channel((await _feed(monkeypatch, posts=[post])).text).find("item")

    enclosure = item.find("enclosure")
    assert enclosure.get("url") == "https://example.test/m/1.jpg"
    assert enclosure.get("type") == "image/jpeg"


async def test_every_attachment_becomes_its_own_enclosure(monkeypatch):
    post = _media_post([{"url": "https://example.test/m/1.jpg", "type": "image",
                         "mime_type": "image/jpeg"},
                        {"url": "https://example.test/m/2.mp4", "type": "video",
                         "mime_type": "video/mp4"}])

    item = _channel((await _feed(monkeypatch, posts=[post])).text).find("item")

    assert len(item.findall("enclosure")) == 2


async def test_an_enclosure_falls_back_to_the_category_type(monkeypatch):
    post = _media_post([{"url": "https://example.test/m/1.bin", "type": "image", "mime_type": None}])

    item = _channel((await _feed(monkeypatch, posts=[post])).text).find("item")

    assert item.find("enclosure").get("type") == "image"


async def test_a_post_without_media_has_no_enclosure(monkeypatch):
    post = _media_post([])

    item = _channel((await _feed(monkeypatch, posts=[post])).text).find("item")

    assert item.find("enclosure") is None

