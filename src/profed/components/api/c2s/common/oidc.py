# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Optional
from urllib.parse import urlparse, urlunparse
from authlib.jose import JsonWebKey, jwt
from profed.http.client import http

_oidc_issuer: str            = ""
_oidc_config: Optional[dict] = None
_jwks:        Optional[dict] = None
 
 
def set_oidc_issuer(issuer: str) -> None:
    global _oidc_issuer, _oidc_config, _jwks
    _oidc_issuer = issuer
    _oidc_config = None
    _jwks        = None
 
 
def get_oidc_issuer() -> str:
    return _oidc_issuer
 
 
async def _fetch_oidc_config(issuer: str) -> dict:
    global _oidc_config
    if _oidc_config is not None:
        return _oidc_config

    parsed = urlparse(issuer)
    url = urlunparse((parsed.scheme,
                      parsed.netloc,
                      "/.well-known/openid-configuration",
                      "",
                      "",
                      ""))
    _oidc_config = await http("GET").json(url)
    return _oidc_config

 
async def _fetch_jwks(issuer: str) -> dict:
    global _jwks
    if _jwks is not None:
        return _jwks

    oidc_config = await _fetch_oidc_config(issuer)
    _jwks = await http("GET").json(oidc_config["jwks_uri"])
    return _jwks 
 
async def validate_token(issuer: str, token: str) -> Optional[dict]:
    try:
        claims = jwt.decode(token,
                            JsonWebKey.import_key_set(await _fetch_jwks(issuer)))
        claims.validate()
        return dict(claims)
    except Exception:
        return None

