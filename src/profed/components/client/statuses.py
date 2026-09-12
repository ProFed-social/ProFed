# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from functools import cache
from hashlib import sha256
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from profed.core.config import config

from .api_client import api_client
from .auth import current_user_optional, requires_login, save_session
from .emoji import grid, tones
from .reactions import after_react, after_unreact, quick_access
from .templating import environment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.delete("/statuses/{id}", response_class=HTMLResponse)
@requires_login
async def delete_status(request: Request, session, id: str):
    response = await api_client().request("DELETE", f"/api/v1/statuses/{id}", token=session["token"])
    if response.status_code != 200:
        logger.warning("deleting a status failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="deleting failed")

    return HTMLResponse("")


async def _status_action(id: str, action: str, token: str, template: str) -> HTMLResponse:
    response = await api_client().post(f"/api/v1/statuses/{id}/{action}", token=token)
    if response.status_code != 200:
        logger.warning("%s failed: %s %s", action, response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail=f"{action} failed")

    return HTMLResponse(environment().get_template(template).render(status=response.json()))


@router.post("/statuses/{id}/reblog", response_class=HTMLResponse)
@requires_login
async def reblog(request: Request, session, id: str):
    return await _status_action(id, "reblog", session["token"], "boost_button.html")


@router.post("/statuses/{id}/unreblog", response_class=HTMLResponse)
@requires_login
async def unreblog(request: Request, session, id: str):
    return await _status_action(id, "unreblog", session["token"], "boost_button.html")


def _render(template: str, status: dict) -> str:
    return environment().get_template(template).render(status=status)


def _button(status: dict) -> str:
    return _render("reaction_button.html", status)


@cache
def _grid(tone: str) -> str:
    return environment().get_template("emoji_grid.html").render(choices=grid(tone), tone=tone)


@cache
def _grid_etag(tone: str) -> str:
    return f'"{sha256(_grid(tone).encode()).hexdigest()[:32]}"'


def _grid_headers(tone: str) -> dict:
    return {"Cache-Control": "public, max-age=86400", "ETag": _grid_etag(tone)}


def _grid_response(request: Request, tone: str) -> Response:
    if tone and tone not in tones():
        raise HTTPException(status_code=404, detail="unknown_skin_tone")

    return (Response(status_code=304, headers=_grid_headers(tone))
            if _grid_etag(tone) in request.headers.get("if-none-match", "") else
            Response(content=_grid(tone),
                     media_type="text/html; charset=utf-8",
                     headers=_grid_headers(tone)))


@router.api_route("/emoji/choices", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def emoji_choices(request: Request):
    return _grid_response(request, "")


@router.api_route("/emoji/choices/{tone}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def emoji_choices_toned(request: Request, tone: str):
    return _grid_response(request, tone)


@router.get("/emoji/picker", response_class=HTMLResponse)
async def emoji_picker(request: Request):
    session = await current_user_optional(request) or {}

    return HTMLResponse(environment().get_template("picker.html")
                        .render(quick=quick_access(session.get("reactions", {}),
                                                   config().get("client", {}).get("quick_reactions", [])),
                                tone=session.get("tone", "")),
                        headers={"Cache-Control": "no-store"})


async def _reaction_action(id: str, method: str, emoji: str, token: str) -> HTMLResponse:
    response = await api_client().request(method,
                                          f"/api/v1/pleroma/statuses/{id}/reactions/{quote(emoji)}",
                                          token=token)
    if response.status_code != 200:
        logger.warning("reaction failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="reaction failed")

    return HTMLResponse(_button(response.json()))


@router.post("/statuses/{id}/react", response_class=HTMLResponse)
@requires_login
async def react(request: Request,
                session,
                id: str,
                emoji: Annotated[str, Form()],
                previous: Annotated[str, Form()] = ""):
    button = await _reaction_action(id, "PUT", emoji, session["token"])
    await save_session(request, {**session, **after_react(session, emoji, previous)})

    return button


@router.post("/statuses/{id}/unreact/{emoji}", response_class=HTMLResponse)
@requires_login
async def unreact(request: Request, session, id: str, emoji: str):
    button = await _reaction_action(id, "DELETE", emoji, session["token"])
    await save_session(request, {**session, **after_unreact(session, emoji)})

    return button

