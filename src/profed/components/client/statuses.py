# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from functools import cache
from hashlib import sha256
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import requires_login
from .emoji import toned
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
def _grid() -> str:
    return environment().get_template("emoji_grid.html").render()


@cache
def _grid_etag() -> str:
    return f'"{sha256(_grid().encode()).hexdigest()[:32]}"'


def _grid_headers() -> dict:
    return {"Cache-Control": "public, max-age=86400", "ETag": _grid_etag()}


@router.api_route("/emoji/choices", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def emoji_choices(request: Request):
    return (Response(status_code=304, headers=_grid_headers())
            if _grid_etag() in request.headers.get("if-none-match", "") else
            Response(content=_grid(),
                     media_type="text/html; charset=utf-8",
                     headers=_grid_headers()))


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
async def react(request: Request, session, id: str, emoji: Annotated[str, Form()], tone: Annotated[str, Form()] = ""):
    return await _reaction_action(id, "PUT", toned(emoji, tone), session["token"])


@router.post("/statuses/{id}/unreact/{emoji}", response_class=HTMLResponse)
@requires_login
async def unreact(request: Request, session, id: str, emoji: str):
    return await _reaction_action(id, "DELETE", emoji, session["token"])

