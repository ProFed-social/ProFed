# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import page_context, requires_login
from .paging import next_query
from .templating import environment

logger = logging.getLogger(__name__)
router = APIRouter()

BOOKMARKS = "/api/v1/bookmarks"

FIRST_PAGE = "limit=20"


async def _page(query: str, token: str):
    response = await api_client().get(BOOKMARKS, params=query, token=token)
    if response.status_code != 200:
        logger.warning("fetching bookmarks failed: %s %s", response.status_code, response.text)
        return [], None
    return response.json(), next_query(response)


async def _rendered(template: str, query: str, request: Request, session) -> HTMLResponse:
    statuses, following = await _page(query, session["token"])
    return HTMLResponse(environment().get_template(template)
                        .render(statuses=statuses,
                                following=following,
                                more_url="/bookmarks/more",
                                **(await page_context(request, session))))


@router.get("/bookmarks", response_class=HTMLResponse)
@requires_login
async def bookmarks(request: Request, session):
    return await _rendered("bookmarks.html", FIRST_PAGE, request, session)


@router.get("/bookmarks/more", response_class=HTMLResponse)
@requires_login
async def more(request: Request, session, following: Optional[str] = None):
    return await _rendered("bookmarks_page.html", following or FIRST_PAGE, request, session)

