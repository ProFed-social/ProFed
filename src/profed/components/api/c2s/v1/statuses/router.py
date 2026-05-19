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
from profed.components.api.c2s.shared.actors.service import resolve_actor, local_account
 
 
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
 
    max_chars = int(_config.get("status_max_characters", 5000))
    if len(body.status) > max_chars:
        raise HTTPException(status_code=422, detail="status too long")
 
    actor_url  = actor_url_from_username(username)
    note_id    = f"{actor_url}/notes/{uuid.uuid4()}"
    created_at = datetime.now(timezone.utc).isoformat()
 
    note = Note(id=note_id,
                attributedTo=actor_url,
                content=body.status,
                published=created_at)
 
    activity_id = f"{actor_url}#create/{uuid.uuid4()}"
    activity = CreateActivity(id=activity_id,
                              actor=actor_url,
                              to=note.to,
                              object=note.model_dump(by_alias=True,
                                                     exclude_none=True))
    payload = activity.model_dump(by_alias=True, exclude_none=True)
    payload["username"] = username
    async with message_bus().topic("activities").publish() as publish:
        await publish({"type":    "created",
                       "payload": payload})
 
    return Status(id=          note_id,
                  created_at=  created_at,
                  visibility=  body.visibility,
                  sensitive=   body.sensitive,
                  spoiler_text=body.spoiler_text,
                  language=    body.language,
                  uri=         note_id,
                  url=         note_id,
                  content=     body.status,
                  account=     local_account(username, await resolve_actor(username)))


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
    actor_url   = actor_url_from_username(username)
    activity    = DeleteActivity(id=f"{actor_url}#delete/{id}",
                                 actor=actor_url,
                                 object=id)
    payload = activity.model_dump(by_alias=True, exclude_none=True)
    payload["username"] = username
    async with message_bus().topic("activities").publish() as publish:
        await publish({"type":    "deleted",
                       "payload": payload})
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

