# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

import pytest

from profed.components.client import auth, statuses
from profed.components.client.templating import STANDARD_TEMPLATES, build_environment


@pytest.fixture(autouse=True)
def templates(monkeypatch):
    environment = build_environment(STANDARD_TEMPLATES, None)
    monkeypatch.setattr(statuses, "environment", lambda: environment)


def _app():
    app = FastAPI()
    app.include_router(statuses.router)

    return app


async def _delete(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.delete(path)


def _resp(status=200):
    r = Mock()
    r.status_code = status
    r.text = ""
    return r


def _login(monkeypatch, token="tok", **session):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": "christof",
                                                "acct": "christof@test.local",
                                                "token": token,
                                                **session}))
    monkeypatch.setattr(statuses, "current_user_optional", auth.current_user_optional)


def _quick_reactions(monkeypatch, *choices):
    monkeypatch.setattr(statuses, "config", lambda: {"client": {"quick_reactions": list(choices)}})


def _saved(monkeypatch):
    saving = AsyncMock()
    monkeypatch.setattr(statuses, "save_session", saving)

    return saving


async def test_delete_status_calls_the_api_with_the_session_token(monkeypatch):
    _login(monkeypatch)
    client = Mock(request=AsyncMock(return_value=_resp(200)))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _delete(_app(), "/statuses/424242")

    assert client.request.call_args.args == ("DELETE", "/api/v1/statuses/424242")
    assert client.request.call_args.kwargs["token"] == "tok"


async def test_delete_status_returns_an_empty_fragment(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_resp(200))))

    response = await _delete(_app(), "/statuses/424242")

    assert response.status_code == 200
    assert response.text == ""


async def test_delete_status_reports_an_api_failure(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_resp(404))))

    response = await _delete(_app(), "/statuses/424242")

    assert response.status_code == 404


async def test_delete_status_redirects_an_anonymous_visitor_to_login(monkeypatch):
    client = Mock(request=AsyncMock())
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    response = await _delete(_app(), "/statuses/424242")

    assert response.status_code == 401
    assert response.headers["HX-Redirect"].startswith("/login?next=")
    client.request.assert_not_awaited()


async def _get(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.get(path)


async def _post(app, path, data=None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.post(path, data=data)


def _boost_resp(reblogged, count=1):
    response = Mock()
    response.status_code = 200
    response.text = ""
    response.json = Mock(return_value={"id": "42", "reblogs_count": count, "reblogged": reblogged})
    return response


async def test_a_reblog_calls_the_api_with_the_session_token(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_boost_resp(True)))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _post(_app(), "/statuses/42/reblog")

    client.post.assert_awaited_once_with("/api/v1/statuses/42/reblog", token="tok")


async def test_an_unreblog_calls_the_undo_endpoint(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_boost_resp(False, 0)))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _post(_app(), "/statuses/42/unreblog")

    client.post.assert_awaited_once_with("/api/v1/statuses/42/unreblog", token="tok")


async def test_a_reblog_returns_the_updated_button(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(post=AsyncMock(return_value=_boost_resp(True, 3))))

    response = await _post(_app(), "/statuses/42/reblog")

    assert 'hx-post="/statuses/42/unreblog"' in response.text
    assert ">3<" in response.text


async def test_a_failing_reblog_is_reported(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(post=AsyncMock(return_value=_resp(404))))

    assert (await _post(_app(), "/statuses/42/reblog")).status_code == 404


def _status_resp(reactions, count=0):
    response = Mock()
    response.status_code = 200
    response.text = ""
    response.json = Mock(return_value={"id": "42",
                                       "favourites_count": count,
                                       "pleroma": {"emoji_reactions": reactions}})
    return response


async def test_a_reaction_calls_the_pleroma_endpoint(monkeypatch):
    _login(monkeypatch)
    client = Mock(request=AsyncMock(return_value=_status_resp([])))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    client.request.assert_awaited_once_with("PUT", "/api/v1/pleroma/statuses/42/reactions/%F0%9F%8E%89", token="tok")


async def test_removing_a_reaction_uses_delete(monkeypatch):
    _login(monkeypatch)
    client = Mock(request=AsyncMock(return_value=_status_resp([])))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _post(_app(), "/statuses/42/unreact/%F0%9F%8E%89")

    assert client.request.await_args.args[0] == "DELETE"


async def test_a_favourite_returns_the_updated_button(monkeypatch):
    _login(monkeypatch)
    reactions = [{"name": "🎉", "count": 2, "me": True}]
    monkeypatch.setattr(statuses,
                        "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp(reactions, count=2))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert 'aria-label="React">🎉' in response.text
    assert "is-reacted" in response.text
    assert ">2<" in response.text


async def test_a_status_without_an_own_reaction_shows_the_heart(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    response = await _post(_app(), "/statuses/42/unreact/%F0%9F%8E%89")

    assert "&#9825;" in response.text or "\u2661" in response.text
    assert "is-reacted" not in response.text


async def test_the_button_carries_the_breakdown_as_its_title(monkeypatch):
    _login(monkeypatch)
    reactions = [{"name": "🎉", "count": 2, "me": True}, {"name": "🐶", "count": 1, "me": False}]
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp(reactions, count=3))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert 'title="🎉 2, 🐶 1"' in response.text


async def test_a_failing_reaction_is_reported(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_resp(404))))

    assert (await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})).status_code == 404


async def test_the_emoji_grid_is_served_with_a_long_cache_lifetime():
    response = await _get(_app(), "/emoji/choices")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=86400"
    assert response.headers["etag"]


async def test_a_matching_etag_answers_with_not_modified():
    etag = (await _get(_app(), "/emoji/choices")).headers["etag"]
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        response = await client.get("/emoji/choices", headers={"If-None-Match": etag})

    assert response.status_code == 304
    assert response.text == ""


async def test_a_head_request_reports_the_size_without_the_body():
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        response = await client.head("/emoji/choices")

    assert response.status_code == 200
    assert response.text == ""
    assert response.headers["etag"]
    assert response.headers["cache-control"] == "public, max-age=86400"


async def test_the_grid_carries_the_emoji_as_a_submit_value():
    response = await _get(_app(), "/emoji/choices")

    assert 'name="emoji" value="🎉"' in response.text


async def test_the_grid_is_the_same_for_every_reader():
    first = await _get(_app(), "/emoji/choices")
    second = await _get(_app(), "/emoji/choices")

    assert first.text == second.text


async def test_the_button_opens_the_picker_without_a_second_request(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert 'popovertarget="picker-42"' in response.text
    assert '<div popover id="picker-42"' in response.text
    assert 'hx-trigger="toggle once from:closest [popover]"' in response.text


async def test_an_own_reaction_offers_the_empty_heart_for_removal(monkeypatch):
    _login(monkeypatch)
    reactions = [{"name": "🎉", "count": 1, "me": True}]
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp(reactions, 1))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert 'hx-post="/statuses/42/unreact/%F0%9F%8E%89"' in response.text


async def test_without_an_own_reaction_there_is_nothing_to_remove(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert "/statuses/42/unreact/" not in response.text


async def test_the_reaction_form_posts_to_the_react_endpoint(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert '<form class="reaction-area" id="reactions-42"' in response.text
    assert 'hx-post="/statuses/42/react"' in response.text


async def test_the_picker_replaces_only_itself(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    picker = response.text[response.text.index('<div class="picker"'):]
    assert 'hx-target="this"' in picker[:picker.index(">") + 200]


async def test_the_grid_uses_no_element_ids():
    response = await _get(_app(), "/emoji/choices")

    assert " id=" not in response.text
    assert "for=" not in response.text


async def test_the_grid_wraps_its_group_radios_in_labels():
    response = await _get(_app(), "/emoji/choices")

    assert '<input type="radio" name="emoji-group"' in response.text
    assert "<label title=" in response.text


async def test_the_grid_offers_every_skin_tone():
    response = await _get(_app(), "/emoji/choices")

    assert 'hx-get="/emoji/choices/light"' in response.text
    assert 'hx-get="/emoji/choices/dark"' in response.text
    assert 'class="tone is-current"' in response.text


async def test_a_toned_grid_carries_the_toned_emoji():
    response = await _get(_app(), "/emoji/choices/medium")

    assert 'value="👍🏽"' in response.text
    assert 'value="🎉"' in response.text


async def test_a_toned_grid_marks_its_own_tone():
    response = await _get(_app(), "/emoji/choices/medium")

    assert 'hx-get="/emoji/choices/medium" title="medium"' in response.text
    assert response.text.count('class="tone is-current"') == 1


async def test_an_unknown_skin_tone_is_not_found():
    assert (await _get(_app(), "/emoji/choices/purple")).status_code == 404


async def test_every_toned_grid_has_its_own_etag():
    plain = (await _get(_app(), "/emoji/choices")).headers["etag"]
    medium = (await _get(_app(), "/emoji/choices/medium")).headers["etag"]

    assert plain != medium


async def test_the_picker_offers_the_configured_choices_to_a_reader_without_a_history(monkeypatch):
    _quick_reactions(monkeypatch, "👍", "❤️", "👏", "💡", "😂")

    response = await _get(_app(), "/emoji/picker")

    assert response.status_code == 200
    assert 'value="👍"' in response.text
    assert 'value="😂"' in response.text


async def test_the_picker_leads_with_the_most_used_emoji(monkeypatch):
    _login(monkeypatch, reactions={"🐶": 7}, tone="")
    _quick_reactions(monkeypatch, "👍", "❤️", "👏", "💡", "😂")

    response = await _get(_app(), "/emoji/picker")

    assert response.text.index('value="🐶"') < response.text.index('value="👍"')


async def test_the_picker_offers_every_tone_of_a_choice(monkeypatch):
    _quick_reactions(monkeypatch, "👍")

    response = await _get(_app(), "/emoji/picker")

    assert 'value="👍"' in response.text
    assert 'value="👍🏻"' in response.text
    assert 'value="👍🏿"' in response.text


async def test_the_picker_marks_the_tone_of_the_session(monkeypatch):
    _login(monkeypatch, reactions={}, tone="medium")
    _quick_reactions(monkeypatch, "👍")

    marked = [button
              for button in (await _get(_app(), "/emoji/picker")).text.split("<button")
              if "is-current" in button]

    assert len(marked) == 1
    assert 'value="👍🏽"' in marked[0]


async def test_the_picker_asks_for_the_grid_in_the_tone_of_the_session(monkeypatch):
    _login(monkeypatch, reactions={}, tone="medium")
    _quick_reactions(monkeypatch, "👍")

    assert 'hx-get="/emoji/choices/medium"' in (await _get(_app(), "/emoji/picker")).text


async def test_the_picker_asks_for_the_plain_grid_without_a_tone(monkeypatch):
    _quick_reactions(monkeypatch, "👍")

    assert 'hx-get="/emoji/choices"' in (await _get(_app(), "/emoji/picker")).text


async def test_the_picker_is_not_cached(monkeypatch):
    _quick_reactions(monkeypatch, "👍")

    assert (await _get(_app(), "/emoji/picker")).headers["cache-control"] == "no-store"


async def test_the_reaction_form_carries_the_own_reaction_as_the_previous_one(monkeypatch):
    _login(monkeypatch)
    reactions = [{"name": "🎉", "count": 1, "me": True}]
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp(reactions, 1))))

    response = await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    assert '<input type="hidden" name="previous" value="🎉">' in response.text


async def test_reacting_counts_the_emoji_up_in_the_session(monkeypatch):
    _login(monkeypatch, reactions={"👍": 2}, tone="")
    saving = _saved(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    await _post(_app(), "/statuses/42/react", {"emoji": "👍🏽", "previous": ""})

    assert saving.await_args.args[1]["reactions"] == {"👍": 3}
    assert saving.await_args.args[1]["tone"] == "medium"
    assert saving.await_args.args[1]["token"] == "tok"


async def test_changing_the_reaction_moves_the_count_over(monkeypatch):
    _login(monkeypatch, reactions={"👍": 2}, tone="")
    saving = _saved(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    await _post(_app(), "/statuses/42/react", {"emoji": "🎉", "previous": "👍"})

    assert saving.await_args.args[1]["reactions"] == {"👍": 1, "🎉": 1}


async def test_taking_a_reaction_back_counts_it_down_in_the_session(monkeypatch):
    _login(monkeypatch, reactions={"🎉": 2}, tone="medium")
    saving = _saved(monkeypatch)
    monkeypatch.setattr(statuses, "api_client",
                        lambda: Mock(request=AsyncMock(return_value=_status_resp([]))))

    await _post(_app(), "/statuses/42/unreact/%F0%9F%8E%89")

    assert saving.await_args.args[1]["reactions"] == {"🎉": 1}
    assert saving.await_args.args[1]["tone"] == "medium"


async def test_a_failing_reaction_leaves_the_session_alone(monkeypatch):
    _login(monkeypatch, reactions={"🎉": 2}, tone="")
    saving = _saved(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_resp(502))))

    await _post(_app(), "/statuses/42/react", {"emoji": "🎉"})

    saving.assert_not_awaited()

