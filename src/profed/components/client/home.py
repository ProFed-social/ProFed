# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .auth import page_context
from .templating import environment

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    template = environment().get_template("home.html")
    return HTMLResponse(template.render(**(await page_context(request))))

