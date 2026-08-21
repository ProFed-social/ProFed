# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
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


async def _messages(id: str, username: str, token: str):
    messages = await _get(f"/api/v1/conversations/{id}/messages", token) or []
    previous = None
    for message in messages:
        own_url = actor_url_from_username(username)
        message["own"] = message["account"]["url"] == own_url
        if message.get("reply_to"):
            message["reply_to"]["own"] = message["reply_to"]["account"]["url"] == own_url
        if previous and message.get("in_reply_to_id") == previous["id"] and message["account"]["url"] == previous["account"]["url"]:
            message["reply_to"] = None
        previous = message
    return messages


async def _view(request: Request, session, active_id, pane: str):
    conversations = await _get("/api/v1/conversations", session["token"]) or []
    active_id = active_id if active_id is not None else (conversations[0]["id"] if conversations else None)
    messages = await _messages(active_id, session["username"], session["token"]) if active_id is not None else []
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

async def reply(request: Request,
                id: str, session,
                status: Annotated[str, Form()],
                in_reply_to_id: Annotated[str, Form()] = ""):
    response = await api_client().post("/api/v1/statuses",
                                       json={"status": status,
                                             "in_reply_to_id": in_reply_to_id or id,
                                             "visibility": "direct"},
                                       token=session["token"])
    if response.status_code != 200:
        logger.warning("posting a reply failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="reply failed")
    messages = await _messages(id, session["username"], session["token"])
    return HTMLResponse(environment().get_template("conversation_messages.html").render(messages=messages))

