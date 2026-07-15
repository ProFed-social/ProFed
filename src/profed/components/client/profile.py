# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .api_client import api_client
from .auth import page_context, current_user_optional, requires_login
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


async def _relationship(account_id, token):
    response = await api_client().get("/api/v1/accounts/relationships",
                                      params={"id[]": account_id},
                                      token=token)
    if response.status_code != 200:
        return None
    data = response.json()
    return data[0] if data else None


def _follow_button(handle, relationship):
    return environment().get_template("follow_button.html").render(handle=handle,
                                                                   relationship=relationship)
async def _follow_action(handle: str, action: str, token: str):
    account = await _account_from_handle(handle)
    response = await api_client().post(f"/api/v1/accounts/{account['id']}/{action}", token=token)
    response.raise_for_status()

    return HTMLResponse(_follow_button(handle, response.json()))


def _viewing_other(account, session):
    return session is not None and account["acct"] != session.get("acct")


@router.get("/@{handle}", response_class=HTMLResponse)
async def profile(request: Request, handle: str):
    account = await _account_from_handle(handle)
    session = await current_user_optional(request)
    relationship = (await _relationship(account["id"], session["token"])
                    if _viewing_other(account, session) else
                    None)
    return HTMLResponse(environment().get_template("profile.html").render(
        account=account,
        statuses=await _account_statuses(account["id"]),
        handle=handle,
        relationship=relationship,
        **(await page_context(request, session))))


@router.post("/@{handle}/follow", response_class=HTMLResponse)
@requires_login
async def follow(request: Request, handle: str, session):
    return await _follow_action(handle, "follow", session["token"])


@router.post("/@{handle}/unfollow", response_class=HTMLResponse)
@requires_login
async def unfollow(request: Request, handle: str, session):
    return await _follow_action(handle, "unfollow", session["token"])

