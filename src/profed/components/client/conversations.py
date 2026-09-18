# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from typing import Annotated, Optional

from .api_client import api_client
from .paging import fetched
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


FIRST_PAGE = "limit=40"


async def _messages(id: str, username: str, token: str, query: str = FIRST_PAGE):
    page, following = await fetched(api_client,
                                    f"/api/v1/conversations/{id}/messages",
                                    query,
                                    token,
                                    f"messages of conversation {id}")
    messages = list(reversed(page))
    previous = None
    for message in messages:
        own_url = actor_url_from_username(username)
        message["own"] = message["account"]["url"] == own_url
        if message.get("reply_to"):
            message["reply_to"]["own"] = message["reply_to"]["account"]["url"] == own_url
        if previous and message.get("in_reply_to_id") == previous["id"] and message["account"]["url"] == previous["account"]["url"]:
            message["reply_to"] = None
        previous = message
    return messages, following


CONVERSATIONS = "/api/v1/conversations"

FIRST_LIST_PAGE = "limit=20"


async def _conversations(token: str, query: str = FIRST_LIST_PAGE):
    return await fetched(api_client, CONVERSATIONS, query, token, "conversations")


async def _view(request: Request, session, active_id, pane: str):
    conversations, following_list = await _conversations(session["token"])
    active_id = active_id if active_id is not None else (conversations[0]["id"] if conversations else None)
    messages, following = (await _messages(active_id, session["username"], session["token"])
                           if active_id is not None else
                           ([], None))
    return HTMLResponse(environment().get_template("conversation_layout.html").render(conversations=conversations,
                                                                                      active_id=active_id,
                                                                                      messages=messages,
                                                                                      following=following,
                                                                                      following_list=following_list,
                                                                                      pane=pane,
                                                                                      **(await page_context(request,
                                                                                                            session))))


@router.get("/conversations", response_class=HTMLResponse)
@requires_login
async def conversation_list(request: Request, session):
    return await _view(request, session, None, "list")


@router.get("/conversations/more", response_class=HTMLResponse)
@requires_login
async def more_conversations(request: Request, session, following: Optional[str] = None):
    conversations, next_page = await _conversations(session["token"], following or FIRST_LIST_PAGE)
    return HTMLResponse(environment().get_template("conversation_list_page.html").render(conversations=conversations,
                                                                                         following=next_page,
                                                                                         active_id=None))


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
    messages, following = await _messages(id, session["username"], session["token"])
    return HTMLResponse(environment().get_template("conversation_messages.html").render(messages=messages,
                                                                                        following=following,
                                                                                        active_id=id))


@router.get("/conversations/{id}/messages/more", response_class=HTMLResponse)
@requires_login
async def more(request: Request, session, id: str, following: Optional[str] = None):
    messages, next_page = await _messages(id,
                                          session["username"],
                                          session["token"],
                                          following or FIRST_PAGE)
    return HTMLResponse(environment().get_template("conversation_messages_page.html")
                        .render(messages=messages,
                                following=next_page,
                                active_id=id))

