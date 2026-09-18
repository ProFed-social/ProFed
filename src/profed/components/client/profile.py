# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from .api_client import api_client
from .paging import fetched
from .auth import page_context, current_user_optional, requires_login
from .templating import environment

router = APIRouter()


async def _account_from_handle(handle: str):
    lookup = await api_client().get("/api/v1/accounts/lookup", params={"acct": handle})
    if lookup.status_code == 404:
        raise HTTPException(status_code=404, detail="Account not found")
    lookup.raise_for_status()

    return lookup.json()


FIRST_PAGE = "limit=20"


async def _account_page(account_id, query, token=None):
    return await fetched(api_client,
                         f"/api/v1/accounts/{account_id}/statuses",
                         query,
                         token,
                         f"statuses for account {account_id}")


async def _account_statuses(account_id, token=None):
    return (await _account_page(account_id, FIRST_PAGE, token))[0]


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
async def _follow_action(handle: str, action: str, token: str) -> HTMLResponse:
    def raise_for_status(response):
        response.raise_for_status()
        return response

    async def extract_json_response(account, action, token):
        return raise_for_status(await api_client().post(f"/api/v1/accounts/{account['id']}/{action}",
                                                        token=token)).json()

    return HTMLResponse(_follow_button(handle, await extract_json_response(await _account_from_handle(handle),
                                                                           action,
                                                                           token)))


def _viewing_other(account, session):
    return session is not None and account["acct"] != session.get("acct")


@router.get("/@{handle}", response_class=HTMLResponse)
async def profile(request: Request, handle: str):
    async def render_template(request, handle, account, session, relationship, statuses, following):
        return environment().get_template("profile.html").render(account=account,
                                                                          statuses=statuses,
                                                                          following=following,
                                                                          more_url=f"/@{handle}/more",
                                                                          handle=handle,
                                                                          relationship=relationship,
                                                                          **(await page_context(request, session)))

    async def render_response(request, handle, account, session):
        return await render_template(request,
                                     handle,
                                     account,
                                     session,
                                     (await _relationship(account["id"], session["token"])
                                      if _viewing_other(account, session) else
                                      None),
                                     *await _account_page(account["id"], FIRST_PAGE, (session or {}).get("token")))

    return HTMLResponse(await render_response(request,
                                              handle,
                                              await _account_from_handle(handle),
                                              await current_user_optional(request)))


@router.get("/@{handle}/more", response_class=HTMLResponse)
async def more(request: Request, handle: str, following: Optional[str] = None):
    async def render_template(request, handle, session, statuses, next_page):
        return environment().get_template("profile_page.html").render(statuses=statuses,
                                                                      following=next_page,
                                                                      more_url=f"/@{handle}/more",
                                                                      show_author=False,
                                                                      **(await page_context(request, session)))
    async def render_response(request, handle, account, session):
        return await render_template(request,
                                     handle,
                                     session,
                                     *(await _account_page(account["id"],
                                                           following or FIRST_PAGE,
                                                           (session or {}).get("token"))))

    return HTMLResponse(await render_response(request,
                                              handle,
                                              await _account_from_handle(handle),
                                              await current_user_optional(request)))


@router.get("/@{handle}/feed.xml")
async def feed(request: Request, handle: str):
    account = await _account_from_handle(handle)
    return Response(environment().get_template("feed.xml").render(account=account,
                                                                  statuses=await _account_statuses(account["id"]),
                                                                  profile_url=str(request.url_for("profile",
                                                                                                  handle=handle)),
                                                                  feed_url=str(request.url)),
                    media_type="application/rss+xml")


@router.post("/@{handle}/follow", response_class=HTMLResponse)
@requires_login
async def follow(request: Request, handle: str, session):
    return await _follow_action(handle, "follow", session["token"])


@router.post("/@{handle}/unfollow", response_class=HTMLResponse)
@requires_login
async def unfollow(request: Request, handle: str, session):
    return await _follow_action(handle, "unfollow", session["token"])

