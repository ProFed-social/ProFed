# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from profed.core.config import config
from profed.core.key_value_store import key_value_store
from profed.identity import domain

from .api_client import api_client


logger = logging.getLogger(__name__)
router = APIRouter()

SESSION_COOKIE = "session"
STATE_COOKIE = "oauth_state"
DEFAULT_SCOPE = "read write"
DEFAULT_SESSION_TTL = 86400
STATE_TTL = 600


def _as_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _session_key(sid):
    return f"client:session:{sid}"


def _oauth_config():
    cfg = config().get("client", {})
    return {"client_id": cfg.get("client_id", ""),
            "client_secret": cfg.get("client_secret", ""),
            "scope": cfg.get("scope", DEFAULT_SCOPE),
            "session_ttl": int(cfg.get("session_ttl", DEFAULT_SESSION_TTL)),
            "cookie_secure": _as_bool(cfg.get("cookie_secure", True))}


async def current_user_optional(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    return None if sid is None else await key_value_store().get(_session_key(sid))


async def current_user(request: Request):
    session = await current_user_optional(request)
    if session is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return session


@router.get("/login")
async def login():
    cfg = _oauth_config()
    state = secrets.token_urlsafe(16)
    params = {"response_type": "code",
              "client_id": cfg["client_id"],
              "redirect_uri": f"https://{domain()}/auth/callback",
              "scope": cfg["scope"],
              "state": state}
    response = RedirectResponse(f"/oauth/authorize?{urlencode(params)}", status_code=302)
    response.set_cookie(STATE_COOKIE,
                        state,
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


async def _username(access_token: str):
    account = await api_client().get("/api/v1/accounts/verify_credentials",
                                     token=access_token)
    account.raise_for_status()
    return account.json()["username"]


async def _start_session(access_token: str, session_ttl):
    sid = secrets.token_urlsafe(32)
    await key_value_store().set(_session_key(sid),
                                {"username": await _username(access_token),
                                 "token": access_token},
                                session_ttl)
    return sid


@router.get("/auth/callback")
async def callback(request: Request, code: str, state: str):
    cfg = _oauth_config()
    if request.cookies.get(STATE_COOKIE) != state:
        raise HTTPException(status_code=400, detail="invalid_state")

    response = RedirectResponse("/", status_code=303)
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
    return response


@router.get("/logout")
async def logout(request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid is not None:
        await key_value_store().delete(_session_key(sid))

    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response

