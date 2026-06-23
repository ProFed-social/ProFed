# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import page_context
from .templating import environment

logger = logging.getLogger(__name__)
router = APIRouter()


async def _account_from_handle(handle: str):
    lookup = await api_client().get("/api/v1/accounts/lookup", params={"acct": handle})
    if lookup.status_code == 404:
        raise HTTPException(status_code=404, detail="Account not found")
    lookup.raise_for_status()

    return lookup.json()


async def _account_statuses(account_id):
    response = await api_client().get(f"/api/v1/accounts/{account_id}/statuses", params={"limit": 20})
    if response.status_code != 200:
        logger.warning("fetching statuses for account %s failed: %s %s",
                       account_id, response.status_code, response.text)
        return []

    return response.json()


@router.get("/@{handle}", response_class=HTMLResponse)
async def profile(request: Request, handle: str):
    account = await _account_from_handle(handle)
    statuses = await _account_statuses(account["id"]) 
    template = environment().get_template("profile.html")

    return HTMLResponse(template.render(account=account,
                                        statuses=statuses,
                                        **(await page_context(request))))

