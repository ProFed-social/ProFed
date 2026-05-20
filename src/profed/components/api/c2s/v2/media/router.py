# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, File, Form, UploadFile
from typing import Annotated, Optional
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.media.upload import process_upload


router = APIRouter()
active = False


def init(config: dict) -> None:
    global active
    active = True


@router.post("/media")
async def upload_media(claims: Annotated[dict, Depends(current_user)],
                       file: UploadFile = File(...),
                       description: Optional[str] = Form(default=None)):
    return await process_upload(claims.get("preferred_username") or claims.get("sub"),
                                file,
                                description)

