# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from .oidc import validate_token, get_oidc_issuer


_bearer = HTTPBearer()
 
 
async def current_user(credentials: Annotated[HTTPAuthorizationCredentials,
                                              Depends(_bearer)]) -> dict:
    claims = await validate_token(get_oidc_issuer(), credentials.credentials)
    if claims is None:
        raise HTTPException(status_code=401, detail="invalid_token")
    return claims

