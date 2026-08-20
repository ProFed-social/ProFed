# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Annotated

from .api_client import api_client
from .auth import page_context, requires_login
from .templating import environment
from profed.identity import actor_url_from_username

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get(path: str, token: str):
    response = await api_client().get(path, token=token)
    if response.status_code != 200:
        logger.warning("fetching %s failed: %s %s", path, response.status_code, response.text)
        return None
    return response.json()


async def _messages(id: str, token: str):
    return await _get(f"/api/v1/conversations/{id}/messages", token) or []


async def _view(request: Request, session, active_id, pane: str):
    conversations = await _get("/api/v1/conversations", session["token"]) or []
    active_id = active_id if active_id is not None else (conversations[0]["id"] if conversations else None)
    messages = await _messages(active_id, session["token"]) if active_id is not None else []
    for message in messages:
        message["own"] = message["account"]["url"] == actor_url_from_username(session["username"])
    return HTMLResponse(environment().get_template("conversation_layout.html").render(conversations=conversations,
                                                                                      active_id=active_id,
                                                                                      messages=messages,
                                                                                      pane=pane,
                                                                                      **(await page_context(request,
                                                                                                            session))))

 
@router.get("/conversations", response_class=HTMLResponse)
@requires_login
async def conversation_list(request: Request, session):
    return await _view(request, session, None, "list")


@router.get("/conversations/{id}", response_class=HTMLResponse)
@requires_login
async def conversation(request: Request, id: str, session):
    return await _view(request, session, id, "view")


@router.post("/conversations/{id}/reply")
@requires_login
async def reply(request: Request, id: str, session, status: Annotated[str, Form()]):
    response = await api_client().post("/api/v1/statuses",
                                       json={"status": status,
                                             "in_reply_to_id": id,
                                             "visibility": "direct"},
                                       token=session["token"])
    if response.status_code != 200:
        logger.warning("posting a reply failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="reply failed")
    return RedirectResponse(f"/conversations/{id}", status_code=303)

