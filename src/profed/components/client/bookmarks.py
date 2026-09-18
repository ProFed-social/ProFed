# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import page_context, requires_login
from .paging import fetched
from .templating import environment

router = APIRouter()

BOOKMARKS = "/api/v1/bookmarks"

FIRST_PAGE = "limit=20"


async def _rendered(template: str, query: str, request: Request, session) -> HTMLResponse:
    statuses, following = await fetched(api_client, BOOKMARKS, query, session["token"], "bookmarks")
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

