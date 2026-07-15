# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Annotated
from profed.core.message_bus import message_bus
from profed.identity import actor_url_from_username, acct_from_username
from profed.models.activity_pub import CreateActivity, DeleteActivity, Note
from profed.models.mastodon import Status, StatusContext
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.actors.service import resolve_actor
from profed.sanitize import sanitize_html


router = APIRouter()
active = False
_config: dict = {}


def init(config: dict) -> None:
    global active, _config
    active = True
    _config = config


class StatusCreate(BaseModel):
    status: str
    visibility: str = "public"
    sensitive: bool = False
    spoiler_text: str = ""
    language: str | None = None


@router.post("/statuses")
async def create_status(body: StatusCreate,
                        claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    if len(body.status) > int(_config.get("status_max_characters", 5000)):
        raise HTTPException(status_code=422, detail="status too long")

    actor_url  = actor_url_from_username(username)
    note = Note(id=f"{actor_url}/notes/{uuid.uuid4()}",
                attributedTo=actor_url,
                content=sanitize_html(body.status),
                summary=sanitize_html(body.spoiler_text) or None,
                published=datetime.now(timezone.utc).isoformat())
    activity = CreateActivity(id=f"{actor_url}#create/{uuid.uuid4()}",
                              actor=actor_url,
                              to=note.to,
                              object=note.model_dump(by_alias=True,
                                                     exclude_none=True))

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Create",
                      object_id=activity.id,
                      payload={"username": username,
                               "activity": {k: v
                                            for k, v in activity.model_dump(by_alias=True,
                                                                            exclude_none=True).items()
                                            if k not in ("id", "type")}})

    return Status(id=note.id,
                  created_at=note.published,
                  visibility=body.visibility,
                  sensitive=body.sensitive,
                  spoiler_text=note.summary or "",
                  language=body.language,
                  uri=note.id,
                  url=note.id,
                  content=note.content,
                  account=await resolve_actor(username))


@router.get("/statuses/{id}")
async def get_status(id: str,
                     claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.delete("/statuses/{id}")
async def delete_status(id: str,
                        claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")
    actor_url = actor_url_from_username(username)

    activity = DeleteActivity(id=f"{actor_url}#delete/{id}",
                              actor=actor_url,
                              object=id)

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Delete",
                      object_id=f"{actor_url}#delete/{id}",
                      payload={"username": username,
                               "activity": activity.as_event_payload()})
    return {}


@router.get("/statuses/{id}/context")
async def status_context(id: str,
                         claims: Annotated[dict, Depends(current_user)] = None):
    return StatusContext()


@router.post("/statuses/{id}/favourite")
async def favourite_status(id: str,
                           claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unfavourite")
async def unfavourite_status(id: str,
                             claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/reblog")
async def reblog_status(id: str,
                        claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unreblog")
async def unreblog_status(id: str,
                          claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/statuses/{id}/favourited_by")
async def favourited_by(id: str,
                        claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.get("/statuses/{id}/reblogged_by")
async def reblogged_by(id: str,
                       claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.post("/statuses/{id}/bookmark")
async def bookmark_status(id: str,
                          claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unbookmark")
async def unbookmark_status(id: str,
                            claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/pin")
async def pin_status(id: str,
                     claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unpin")
async def unpin_status(id: str,
                       claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.put("/statuses/{id}")
async def edit_status(id: str,
                      claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/statuses/{id}/history")
async def status_history(id: str,
                         claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/statuses/{id}/source")
async def status_source(id: str,
                        claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/scheduled_statuses")
async def get_scheduled_statuses(claims: Annotated[dict, Depends(current_user)]):
    return []

