# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import requires_login
from .templating import environment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.delete("/statuses/{id}", response_class=HTMLResponse)
@requires_login
async def delete_status(request: Request, session, id: str):
    response = await api_client().request("DELETE", f"/api/v1/statuses/{id}", token=session["token"])
    if response.status_code != 200:
        logger.warning("deleting a status failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="deleting failed")

    return HTMLResponse("")


async def _boost_action(id: str, action: str, token: str) -> HTMLResponse:
    response = await api_client().post(f"/api/v1/statuses/{id}/{action}", token=token)
    if response.status_code != 200:
        logger.warning("%s failed: %s %s", action, response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail=f"{action} failed")

    return HTMLResponse(environment().get_template("boost_button.html").render(status=response.json()))


@router.post("/statuses/{id}/reblog", response_class=HTMLResponse)
@requires_login
async def reblog(request: Request, session, id: str):
    return await _boost_action(id, "reblog", session["token"])


@router.post("/statuses/{id}/unreblog", response_class=HTMLResponse)
@requires_login
async def unreblog(request: Request, session, id: str):
    return await _boost_action(id, "unreblog", session["token"])

