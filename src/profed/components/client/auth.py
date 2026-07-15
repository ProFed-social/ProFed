# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import wraps
import inspect
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from profed.core.config import config
from profed.core.key_value_store import key_value_store
from profed.identity import domain

from .api_client import api_client


logger = logging.getLogger(__name__)
router = APIRouter()

SESSION_COOKIE = "session"
STATE_COOKIE = "oauth_state"
RETURN_COOKIE = "oauth_return"
DEFAULT_SCOPE = "read write"
DEFAULT_SESSION_TTL = 86400
STATE_TTL = 600


def _session_key(sid):
    return f"client:session:{sid}"


def _safe_next(target):
    target = target or ""
    return (target
            if target.startswith("/") and
               not target.startswith(("//", "/\\")) and
               target.split("?", 1)[0] != "/login" else
            "/")


def _full_path(request):
    return request.url.path + (f"?{request.url.query}" if request.url.query else "")


def _login_url(request):
    return "/login?" + urlencode({"next": _safe_next(_full_path(request))})


async def current_user_optional(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    return None if sid is None else await key_value_store().get(_session_key(sid))


async def current_user(request: Request):
    session = await current_user_optional(request)
    if session is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return session


async def page_context(request):
    return {"current_username": (await current_user_optional(request) or {}).get("username"),
            "login_url": _login_url(request)}

def _login_response(request):
    return (RedirectResponse(_login_url(request), status_code=303)
            if request.method == "GET" else
            Response(status_code=401, headers={"HX-Redirect": _login_url(request)}))


def requires_login(f):
    @wraps(f)
    async def w(*args, **kwargs):
        request = kwargs["request"]
        session = await current_user_optional(request)

        return (_login_response(request)
                if session is None else
                await f(*args, **{**kwargs, "session": session}))

    sig = inspect.signature(f)
    w.__signature__ = sig.replace(parameters=[p
                                              for name, p in sig.parameters.items()
                                              if name != "session"])
    return w


@router.get("/login")
async def login(request: Request):
    cfg = config().get("client", {})
    state = secrets.token_urlsafe(16)
    params = urlencode({'response_type': 'code',
                        'client_id': cfg['client_id'],
                        'redirect_uri': f'https://{domain()}/auth/callback',
                        'scope': cfg['scope'],
                        'state': state})
    response = RedirectResponse(f"/oauth/authorize?{params}", status_code=302)
    response.set_cookie(STATE_COOKIE,
                        state,
                        max_age=STATE_TTL,
                        httponly=True,
                        secure=cfg["cookie_secure"],
                        samesite="lax")
    target = _safe_next(request.query_params.get("next"))
    if target != "/":
        response.set_cookie(RETURN_COOKIE,
                            target,
                            max_age=STATE_TTL,
                            httponly=True,
                            secure=cfg["cookie_secure"],
                            samesite="lax")
    return response


async def _access_token(code: str, client_id: str, client_secret: str):
    token_response = await api_client().post("/oauth/token",
                                             data={"grant_type": "authorization_code",
                                                   "code": code,
                                                   "client_id": client_id,
                                                   "client_secret": client_secret})
    if token_response.status_code != 200:
        logger.warning("token exchange failed: %s %s", token_response.status_code, token_response.text)
        raise HTTPException(status_code=502, detail="token_exchange_failed")
    return token_response.json()["access_token"]


async def _account(access_token: str):
    account = await api_client().get("/api/v1/accounts/verify_credentials",
                                     token=access_token)
    account.raise_for_status()
    return account.json()


async def _start_session(access_token: str, session_ttl):
    sid = secrets.token_urlsafe(32)
    me = await _account(access_token)
    await key_value_store().set(_session_key(sid),
                                {"username": me["username"],
                                 "acct": me["acct"],
                                 "token": access_token},
                                session_ttl)
    return sid


@router.get("/auth/callback")
async def callback(request: Request, code: str, state: str):
    cfg = config().get("client", {})
    if request.cookies.get(STATE_COOKIE) != state:
        raise HTTPException(status_code=400, detail="invalid_state")

    response = RedirectResponse(_safe_next(request.cookies.get(RETURN_COOKIE)), status_code=303)
    response.set_cookie(SESSION_COOKIE,
                        await _start_session(await _access_token(code,
                                                                 cfg["client_id"],
                                                                 cfg["client_secret"]),
                                             cfg["session_ttl"]),
                        max_age=cfg["session_ttl"],
                        httponly=True,
                        secure=cfg["cookie_secure"],
                        samesite="lax")
    response.delete_cookie(STATE_COOKIE)
    response.delete_cookie(RETURN_COOKIE)
    return response


@router.get("/logout")
async def logout(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid is not None:
        await key_value_store().delete(_session_key(sid))

    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response

