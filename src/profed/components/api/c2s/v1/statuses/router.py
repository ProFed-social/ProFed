# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Annotated
from profed.core.message_bus import message_bus
from profed.identity import actor_url_from_username, acct_from_username
from profed.models.activity_pub import CreateActivity, Note
from profed.components.api.c2s.auth import current_user
 
 
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
 
    return {"id":                note_id,
            "created_at":        created_at,
            "visibility":        body.visibility,
            "sensitive":         body.sensitive,
            "spoiler_text":      body.spoiler_text,
            "language":          body.language,
            "uri":               note_id,
            "url":               note_id,
            "content":           body.status,
            "account":           {"id":              username,
                                  "username":        username,
                                  "acct":            acct_from_username(username),
                                  "display_name":    username,
                                  "locked":          False,
                                  "created_at":      "1970-01-01T00:00:00.000Z",
                                  "note":            "",
                                  "url":             actor_url,
                                  "avatar":          "",
                                  "avatar_static":   "",
                                  "header":          "",
                                  "header_static":   "",
                                  "followers_count": 0,
                                  "following_count": 0,
                                  "statuses_count":  0,
                                  "emojis":          [],
                                  "fields":          []},
            "media_attachments": [],
            "mentions":          [],
            "tags":              [],
            "emojis":            [],
            "card":              None,
            "poll":              None,
            "in_reply_to_id":    None,
            "reblog":            None,
            "replies_count":     0,
            "reblogs_count":     0,
            "favourites_count":  0}

