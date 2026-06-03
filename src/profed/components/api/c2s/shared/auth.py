# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from profed.components.api.c2s.oauth.projection import get_token
from .oidc import validate_token, get_oidc_issuer


_bearer = HTTPBearer()
_bearer_optional = HTTPBearer(auto_error=False) 


async def _claims_for(credentials: HTTPAuthorizationCredentials) -> dict | None:
    token = get_token(credentials.credentials)
    return ({"preferred_username": token["username"],
             "sub": token["username"]}
            if token is not None else
            await validate_token(get_oidc_issuer(), credentials.credentials))

 
async def current_user(credentials: Annotated[HTTPAuthorizationCredentials,
                                              Depends(_bearer)]) -> dict:
    claims = await _claims_for(credentials)

    if claims is None:
        raise HTTPException(status_code=401, detail="invalid_token")

    return claims


async def current_user_optional(credentials: Annotated[HTTPAuthorizationCredentials | None,
                                                       Depends(_bearer_optional)] = None) -> dict | None:
    return None if credentials is None else await _claims_for(credentials)

