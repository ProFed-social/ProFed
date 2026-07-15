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


async def _home_timeline(token: str):
    response = await api_client().get("/api/v1/timelines/home", params={"limit": 20}, token=token)
    if response.status_code != 200:
        logger.warning("fetching home timeline failed: %s %s", response.status_code, response.text)
        return []
    return response.json()


@router.get("/", response_class=HTMLResponse)
@requires_login
async def home(request: Request, session):
    return HTMLResponse(environment().get_template("home.html")
                        .render(statuses=await _home_timeline(session["token"]),
                                **(await page_context(request, session))))

