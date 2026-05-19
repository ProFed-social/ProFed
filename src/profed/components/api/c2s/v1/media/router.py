# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from profed.components.api.c2s.shared.auth import current_user


router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


@router.post("/media")
async def upload_media(claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=422,
                        detail="media_upload_not_supported")

