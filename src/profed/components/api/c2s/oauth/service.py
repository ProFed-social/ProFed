# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import time
import secrets
import httpx
from typing import Optional
from urllib.parse import urlencode, urlunparse, urlparse
from authlib.jose import JsonWebKey, jwt
from profed.core.message_bus import message_bus
 
 
_oidc_config: Optional[dict] = None
_jwks: Optional[dict] = None
CODE_TTL = 600
 
 
async def _fetch_oidc_config(issuer: str) -> dict:
    global _oidc_config
    if _oidc_config is None:
        parsed = urlparse(issuer)
        url = urlunparse((parsed.scheme,
                          parsed.netloc,
                          "/.well-known/openid-configuration",
                          "", "", ""))

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            _oidc_config = response.json()

    return _oidc_config
 
 
async def _fetch_jwks(issuer: str) -> dict:
    global _jwks
    if _jwks is None:
        oidc_config = await _fetch_oidc_config(issuer)
        async with httpx.AsyncClient() as client:
            response = await client.get(oidc_config["jwks_uri"])
            response.raise_for_status()
            _jwks = response.json()

    return _jwks
 
 
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
    async with httpx.AsyncClient() as client:
        response = await client.post(
            oidc_config["token_endpoint"],
            data={"grant_type":    "authorization_code",
                  "code":           code,
                  "redirect_uri":   callback_url,
                  "client_id":      nc_client_id,
                  "client_secret":  nc_client_secret})
        response.raise_for_status()

        return response.json()
 
 
async def validate_token(issuer: str, token: str) -> Optional[dict]:
    try:
        jwks = await _fetch_jwks(issuer)
        key = JsonWebKey.import_key_set(jwks)
        claims = jwt.decode(token, key)
        claims.validate()
        return dict(claims)
    except Exception:
        return None
 
 
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

