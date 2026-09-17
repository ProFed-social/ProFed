# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.pagination import paginated
from profed.components.api.c2s.profed.timeline import service


router = APIRouter()
active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/timeline")
@paginated(cursor=lambda block: block["cursor"])
async def timeline(claims: Annotated[dict, Depends(current_user)],
                   limit: int = Query(default=20, ge=1, le=40),
                   max_id: Optional[str] = Query(default=None)):
    username = claims.get("preferred_username") or claims.get("sub")
    blocks = await service.timeline(username, max_id=int(max_id) if max_id is not None else None, limit=limit)
    return [{"parts": block["parts"],
             "booster": block["booster"],
             "boosted": sorted(block["boosted"]),
             "cursor": str(block["cursor"])}
            async for block in blocks]

