# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends
from typing import Annotated
from profed.components.api.c2s.shared.auth import current_user


router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/filters")
async def get_filters(claims: Annotated[dict, Depends(current_user)]):
    return []

