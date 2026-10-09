# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from profed.components.client import auth, compose, posting, templating


_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)


def _serving(monkeypatch, client):
    monkeypatch.setattr(compose, "api_client", lambda: client)
    monkeypatch.setattr(posting, "api_client", lambda: client)

    return client


def _app(monkeypatch):
    monkeypatch.setattr(compose, "environment", lambda: _ENV)

    app = FastAPI()
    app.include_router(compose.router)

    return app


async def _post(app, path, data):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.post(path, data=data)


def _resp(status=200, json_data=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.text = ""
    return r


def _status(content="<p>hello</p>"):
    return {"id": "https://test.local/actors/christof/notes/1",
            "content": content,
            "created_at": "2026-07-16T10:00:00Z",
            "reblogs_count": 0,
            "favourites_count": 0,
            "account": {"url": "https://test.local/@christof",
                        "acct": "christof@test.local",
                        "username": "christof",
                        "display_name": "Christof",
                        "avatar": None}}


def _login(monkeypatch, token="tok"):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": "christof",
                                                "acct": "christof@test.local",
                                                "token": token}))


async def test_compose_posts_the_status_to_the_api(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hello"})

    assert client.post.call_args.args[0] == "/api/v1/statuses"
    assert client.post.call_args.kwargs["json"] == {"status": "hello", "visibility": "public"}
    assert client.post.call_args.kwargs["token"] == "tok"


async def test_compose_includes_in_reply_to_id_when_replying(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "in_reply_to_id": "42"})

    assert client.post.call_args.kwargs["json"] == {"status": "hi",
                                                    "visibility": "public",
                                                    "in_reply_to_id": "42"}


async def test_compose_returns_the_new_status_as_a_fragment(monkeypatch):
    _login(monkeypatch)
    _serving(monkeypatch, Mock(post=AsyncMock(return_value=_resp(200, _status("<p>a new post</p>")))))

    response = await _post(_app(monkeypatch), "/compose", {"status": "a new post"})

    assert response.status_code == 200
    assert "a new post" in response.text
    assert "h-entry status" in response.text
    assert "<html" not in response.text


async def test_compose_reports_an_api_failure(monkeypatch):
    _login(monkeypatch)
    _serving(monkeypatch, Mock(post=AsyncMock(return_value=_resp(422))))

    response = await _post(_app(monkeypatch), "/compose", {"status": "x" * 6000})

    assert response.status_code == 422


async def test_compose_redirects_an_anonymous_visitor_to_login(monkeypatch):
    client = Mock(post=AsyncMock())
    _serving(monkeypatch, client)

    response = await _post(_app(monkeypatch), "/compose", {"status": "hello"})

    assert response.status_code == 401
    assert response.headers["HX-Redirect"].startswith("/login?next=")
    client.post.assert_not_awaited()


def _upload(file_id="m1"):
    return _resp(200, {"id": file_id, "type": "image", "url": f"https://test.local/media/{file_id}"})


async def _post_multipart(app, path, data, files=None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.post(path, data=data, files=files or {})


async def test_compose_carries_the_chosen_visibility(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "visibility": "private"})

    assert client.post.call_args.kwargs["json"]["visibility"] == "private"


async def test_compose_carries_a_content_warning(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "spoiler_text": "Spoiler"})

    assert client.post.call_args.kwargs["json"]["spoiler_text"] == "Spoiler"


async def test_a_content_warning_marks_the_media_as_sensitive(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "spoiler_text": "Spoiler"})

    assert client.post.call_args.kwargs["json"]["sensitive"] is True


async def test_a_post_without_a_warning_is_not_sensitive(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi"})

    assert "sensitive" not in client.post.call_args.kwargs["json"]


async def test_compose_carries_the_chosen_language(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "language": "de"})

    assert client.post.call_args.kwargs["json"]["language"] == "de"


async def test_a_region_we_support_is_kept_as_it_is(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "language": "pt-BR"})

    assert client.post.call_args.kwargs["json"]["language"] == "pt-BR"


async def test_a_language_written_in_the_wrong_case_still_counts(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "language": "PT-br"})

    assert client.post.call_args.kwargs["json"]["language"] == "pt-BR"


async def test_a_language_with_a_region_keeps_only_what_we_know(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi", "language": "de-CH"})

    assert client.post.call_args.kwargs["json"]["language"] == "de"


async def test_a_language_nobody_knows_is_left_off_instead_of_failing(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    response = await _post(_app(monkeypatch), "/compose", {"status": "hi", "language": "Klingonisch"})

    assert response.status_code == 200
    assert "language" not in client.post.call_args.kwargs["json"]


async def test_a_post_without_extras_stays_minimal(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi"})

    assert client.post.call_args.kwargs["json"] == {"status": "hi", "visibility": "public"}


async def test_a_chosen_image_is_uploaded_before_the_status(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(side_effect=[_upload("m1"), _resp(200, _status())]))
    _serving(monkeypatch, client)

    await _post_multipart(_app(monkeypatch), "/compose",
                          {"status": "look", "media_descriptions": "Ein Diagramm"},
                          {"media": ("a.png", b"\x89PNG", "image/png")})

    first, second = client.post.call_args_list
    assert first.args[0] == "/api/v1/media"
    assert first.kwargs["files"]["file"] == ("a.png", b"\x89PNG", "image/png")
    assert first.kwargs["data"] == {"description": "Ein Diagramm"}
    assert second.args[0] == "/api/v1/statuses"
    assert second.kwargs["json"]["media_ids"] == ["m1"]


async def test_several_images_keep_their_order_and_alt_texts(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(side_effect=[_upload("first"), _upload("second"), _resp(200, _status())]))
    _serving(monkeypatch, client)

    await _post_multipart(_app(monkeypatch), "/compose",
                          {"status": "look", "media_descriptions": ["Erstes", "Zweites"]},
                          [("media", ("a.png", b"a", "image/png")), ("media", ("b.png", b"b", "image/png"))])

    uploads = client.post.call_args_list[:2]
    assert [call.kwargs["data"]["description"] for call in uploads] == ["Erstes", "Zweites"]
    assert client.post.call_args.kwargs["json"]["media_ids"] == ["first", "second"]


async def test_an_image_without_an_alt_text_is_uploaded_anyway(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(side_effect=[_upload("m1"), _resp(200, _status())]))
    _serving(monkeypatch, client)

    await _post_multipart(_app(monkeypatch), "/compose", {"status": "look"},
                          {"media": ("a.png", b"a", "image/png")})

    assert client.post.call_args_list[0].kwargs["data"] == {"description": ""}


async def test_a_failing_upload_stops_the_post(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(side_effect=[_resp(422), _resp(200, _status())]))
    _serving(monkeypatch, client)

    response = await _post_multipart(_app(monkeypatch), "/compose", {"status": "look"},
                                     {"media": ("a.png", b"a", "image/png")})

    assert response.status_code == 422
    assert client.post.call_count == 1


async def test_a_post_without_images_uploads_nothing(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    await _post(_app(monkeypatch), "/compose", {"status": "hi"})

    assert client.post.call_count == 1
    assert "media_ids" not in client.post.call_args.kwargs["json"]


async def test_the_empty_file_part_a_browser_always_sends_is_ignored(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    _serving(monkeypatch, client)

    response = await _post_multipart(_app(monkeypatch), "/compose",
                                     {"status": "hi", "visibility": "public", "in_reply_to_id": "",
                                      "spoiler_text": "", "language": ""},
                                     {"media": ("", b"", "application/octet-stream")})

    assert response.status_code == 200
    assert client.post.call_count == 1
    assert "media_ids" not in client.post.call_args.kwargs["json"]

