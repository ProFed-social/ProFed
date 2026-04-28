# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import time
import secrets
from typing import Optional
from urllib.parse import urlencode
from profed.core.message_bus import message_bus
from profed.http.client import http
from ..shared.oidc import _fetch_oidc_config 
 
_oidc_config: Optional[dict] = None
_jwks: Optional[dict] = None
CODE_TTL = 600
 
 
async def authorization_url(issuer: str,
                            client_id: str,
                            callback_url: str,
                            state: str,
                            scope: str = "openid profile email") -> str:
    oidc_config = await _fetch_oidc_config(issuer)
    params = urlencode({"client_id": client_id,
                        "redirect_uri": callback_url,
                        "response_type": "code",
                        "scope": scope,
                        "state": state})

    return f"{oidc_config['authorization_endpoint']}?{params}"
 
 
async def exchange_code(issuer: str,
                        nc_client_id: str,
                        nc_client_secret: str,
                        callback_url: str,
                        code: str) -> dict:
    oidc_config = await _fetch_oidc_config(issuer)

    return await http("POST").json(
        oidc_config["token_endpoint"],
        data={"grant_type":    "authorization_code",
              "code":           code,
              "redirect_uri":   callback_url,
              "client_id":      nc_client_id,
              "client_secret":  nc_client_secret})
 
 
async def issue_code(client_id: str,
                     username: str,
                     id_token: str) -> str:
    code = secrets.token_urlsafe(32)

    async with message_bus().topic("oauth_codes").publish() as publish:
        await publish({"type": "issued",
                       "payload": {"code":       code,
                                   "client_id":  client_id,
                                   "username":   username,
                                   "id_token":   id_token,
                                   "expires_at": time.time() + CODE_TTL}})

    return code
 
 
async def consume_code(code: str) -> None:
    async with message_bus().topic("oauth_codes").publish() as publish:
        await publish({"type": "consumed",
                       "payload": {"code": code}})

