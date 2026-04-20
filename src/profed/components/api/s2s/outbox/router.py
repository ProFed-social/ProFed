# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, HTTPException, Path
from profed.components.api.s2s.outbox.models import OrderedCollection
from profed.components.api.s2s.outbox.service import resolve_outbox
from profed.components.api.http import ActivityPubJSONResponse

router = APIRouter()


@router.get("/actors/{username}/outbox",
            response_model=OrderedCollection,
            response_class=ActivityPubJSONResponse)
async def outbox(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$")):
    try:
        outbox = await resolve_outbox(username)
        if outbox is None:
            raise HTTPException(status_code=404)

        return outbox
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500)
