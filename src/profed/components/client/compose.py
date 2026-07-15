# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from typing import Annotated

from .api_client import api_client
from .auth import requires_login
from .templating import environment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/compose", response_class=HTMLResponse)
@requires_login
async def compose(request: Request, session, status: Annotated[str, Form()]):
    response = await api_client().post("/api/v1/statuses",
                                       json={"status": status, "visibility": "public"},
                                       token=session["token"])
    if response.status_code != 200:
        logger.warning("posting a status failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="posting failed")

    return HTMLResponse(environment().get_template("status.html").render(status=response.json()))

