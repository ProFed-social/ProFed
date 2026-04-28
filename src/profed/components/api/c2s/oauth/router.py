# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import secrets
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from .projection import get_app, get_code
from .service import (authorization_url,
                      exchange_code,
                      issue_code,
                      consume_code)
from ..shared.oidc import validate_token, set_oidc_issuer
 
 
router = APIRouter()
 

_config: dict = {}
_pending: dict[str, tuple[str, str, str]] = {}
 
 
def init(config: dict) -> None:
    global _config
    _config = config
    set_oidc_issuer(config.get("oidc_issuer", ""))
 
 
@router.get("/oauth/authorize")
async def authorize(response_type: str = Query(),
                    client_id: str = Query(),
                    redirect_uri: str = Query(),
                    scope: str = Query(default="read"),
                    state: str = Query(default="")):
    if response_type != "code":
        raise HTTPException(status_code=400, detail="unsupported_response_type")

    app = get_app(client_id)
    if app is None:
        raise HTTPException(status_code=401, detail="invalid_client")

    if redirect_uri not in app["redirect_uris"].split():
        raise HTTPException(status_code=400, detail="invalid_redirect_uri")
 
    nc_state = secrets.token_urlsafe(16)
    _pending[nc_state] = (client_id, redirect_uri, state)
 
    url = await authorization_url(issuer=_config["oidc_issuer"],
                                  client_id=_config["oidc_client_id"],
                                  callback_url=_config["oidc_callback_url"],
                                  state=nc_state)
    return RedirectResponse(url)
 
 
@router.get("/oauth/callback")
async def callback(code: str = Query(),
                    state: str = Query()):
    pending = _pending.pop(state, None)
    if pending is None:
        raise HTTPException(status_code=400, detail="invalid_state")

    client_id, redirect_uri, original_state = pending
    try:
        tokens = await exchange_code(issuer=_config["oidc_issuer"],
                                     nc_client_id=_config["oidc_client_id"],
                                     nc_client_secret=_config["oidc_client_secret"],
                                     callback_url=_config["oidc_callback_url"],
                                     code=code)
    except Exception:
        raise HTTPException(status_code=502, detail="upstream_error")
 
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="no_id_token")
 
    claims = await validate_token(_config["oidc_issuer"], id_token)
    if claims is None:
        raise HTTPException(status_code=502, detail="invalid_token")
 
    username = claims.get("preferred_username") or claims.get("sub")
    profed_code = await issue_code(client_id, username, id_token)
 
    params = urlencode({"code": profed_code, "state": original_state})
    return RedirectResponse(f"{redirect_uri}?{params}")
 
 
@router.post("/oauth/token")
async def token(request: Request):
    form = await request.form()
    grant_type    = form.get("grant_type")
    code          = form.get("code")
    client_id     = form.get("client_id")
    client_secret = form.get("client_secret")
 
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    app = get_app(client_id)
    if app is None or app["client_secret"] != client_secret:
        raise HTTPException(status_code=401, detail="invalid_client")

    entry = get_code(code)
    if entry is None or entry["client_id"] != client_id:
        raise HTTPException(status_code=400, detail="invalid_grant")
 
    await consume_code(code)
    return {"access_token": entry["id_token"],
            "token_type":   "Bearer",
            "scope":        app["scopes"]}

