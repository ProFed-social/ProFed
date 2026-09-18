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

TIMELINE = "/api/profed/timeline"

FIRST_PAGE = "limit=20"


async def _rendered(template: str, query: str, request: Request, session) -> HTMLResponse:
    blocks, following = await fetched(api_client, TIMELINE, query, session["token"], "the home timeline")
    return HTMLResponse(environment().get_template(template)
                        .render(blocks=blocks,
                                following=following,
                                more_url="/timeline/more",
                                **(await page_context(request, session))))


@router.get("/", response_class=HTMLResponse)
@requires_login
async def home(request: Request, session):
    return await _rendered("home.html", FIRST_PAGE, request, session)


@router.get("/timeline/more", response_class=HTMLResponse)
@requires_login
async def more(request: Request, session, following: Optional[str] = None):
    return await _rendered("timeline_page.html", following or FIRST_PAGE, request, session)

