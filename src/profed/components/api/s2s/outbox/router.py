# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, HTTPException, Path
from profed.components.api.s2s.outbox.models import OrderedCollection
from profed.components.api.s2s.outbox.service import resolve_outbox, resolve_note
from profed.components.api.http import ActivityPubJSONResponse

router = APIRouter()


@router.get("/actors/{username}/outbox",
            response_model=OrderedCollection,
            response_class=ActivityPubJSONResponse)
async def outbox(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$")):
    outbox = await resolve_outbox(username)
    if outbox is None:
        raise HTTPException(status_code=404)
    return outbox


@router.get("/actors/{username}/notes/{note_id}", response_class=ActivityPubJSONResponse)
async def note(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$"), note_id: str = Path(pattern=r"^[a-zA-Z0-9_-]+$")):
    resolved = await resolve_note(username, note_id)
    if resolved is None:
        raise HTTPException(status_code=404)
    return ActivityPubJSONResponse(content=resolved, status_code=410 if resolved["type"] == "Tombstone" else 200)

