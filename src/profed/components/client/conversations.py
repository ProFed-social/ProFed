# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
 
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
 
from .api_client import api_client
from .auth import page_context, requires_login
from .templating import environment
 
logger = logging.getLogger(__name__)
router = APIRouter()
 
 
async def _get(path: str, token: str):
    response = await api_client().get(path, token=token)
    if response.status_code != 200:
        logger.warning("fetching %s failed: %s %s", path, response.status_code, response.text)
        return None
    return response.json()
 
 
@router.get("/conversations", response_class=HTMLResponse)
@requires_login
async def conversation_list(request: Request, session):
    return HTMLResponse(environment().get_template("conversation_list.html")
                        .render(conversations=await _get("/api/v1/conversations", session["token"]) or [],
                                **(await page_context(request, session))))
 
 
@router.get("/conversations/{id}", response_class=HTMLResponse)
@requires_login
async def conversation(request: Request, id: str, session):
    root = await _get(f"/api/v1/statuses/{id}", session["token"])
    context = await _get(f"/api/v1/statuses/{id}/context", session["token"]) or {}
    messages = sorted((message
                       for message in [root, *context.get("descendants", [])]
                       if message is not None),
                      key=lambda message: message["created_at"])
    return HTMLResponse(environment().get_template("conversation.html")
                        .render(messages=messages,
                                **(await page_context(request, session))))

