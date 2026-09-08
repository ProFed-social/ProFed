# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import requires_login
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
 
 
async def _status_json(id: str, token: str) -> dict:
    response = await api_client().get(f"/api/v1/statuses/{id}", token=token)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="status not found")
 
    return response.json()
 
 
@router.get("/statuses/{id}/reactions", response_class=HTMLResponse)
@requires_login
async def reactions(request: Request, session, id: str):
    return HTMLResponse(_button(await _status_json(id, session["token"])))


@router.get("/statuses/{id}/reactions/choices", response_class=HTMLResponse)
@requires_login
async def reaction_choices(request: Request, session, id: str):
    return HTMLResponse(_render("reaction_choices.html", await _status_json(id, session["token"])))
 
 
async def _reaction_action(id: str, method: str, emoji: str, token: str) -> HTMLResponse:
    response = await api_client().request(method,
                                          f"/api/v1/pleroma/statuses/{id}/reactions/{quote(emoji)}",
                                          token=token)
    if response.status_code != 200:
        logger.warning("reaction failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="reaction failed")
 
    return HTMLResponse(_button(response.json()))
 
 
@router.post("/statuses/{id}/react/{emoji}", response_class=HTMLResponse)
@requires_login
async def react(request: Request, session, id: str, emoji: str):
    return await _reaction_action(id, "PUT", emoji, session["token"])
 
 
@router.post("/statuses/{id}/unreact/{emoji}", response_class=HTMLResponse)
@requires_login
async def unreact(request: Request, session, id: str, emoji: str):
    return await _reaction_action(id, "DELETE", emoji, session["token"])

