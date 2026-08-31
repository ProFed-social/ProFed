# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Annotated
from profed.core.message_bus import message_bus
from profed.identity import actor_url_from_username, heuristic_acct
from profed.models.activity_pub import (AnnounceActivity,
                                        CreateActivity,
                                        DeleteActivity,
                                        Note,
                                        UndoAnnounceActivity)
from profed.models.mastodon import Status, StatusContext
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.actors.service import resolve_actor
from profed.models.mastodon import mentions_from_tag
from profed.components.api.c2s.shared.known_accounts.storage import storage as _known_accounts_storage
from profed.components.api.c2s.shared.statuses import as_objects, service
from profed.components.api.c2s.shared.conversations import storage as conversations_storage
from profed.sanitize import sanitize_html
from profed import mentions

_PUBLIC = "https://www.w3.org/ns/activitystreams#Public"

router = APIRouter()
active = False
_config: dict = {}


async def _preliminary_lookup(acct: str):
    row = await (await _known_accounts_storage()).get_by_acct(acct)
    return row["actor_url"] if row else None


_preliminary_resolver = mentions.resolver(_preliminary_lookup)


def init(config: dict) -> None:
    global active, _config
    active = True
    _config = config


async def _mention(actor_url: str) -> dict:
    account = await (await _known_accounts_storage()).get_by_actor_url(actor_url)
    acct = account["acct"] if account else heuristic_acct(actor_url)
    return {"type": "Mention", "href": actor_url, "name": "@" + acct}


class StatusCreate(BaseModel):
    status: str
    visibility: str = "public"
    sensitive: bool = False
    spoiler_text: str = ""
    language: str | None = None
    in_reply_to_id: str | None = None


@router.post("/statuses")
async def create_status(body: StatusCreate, claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    if len(body.status) > int(_config.get("status_max_characters", 5000)):
        raise HTTPException(status_code=422, detail="status too long")

    async def make_note(actor_url, in_reply_to):
        recipients = (await (await conversations_storage.storage()).recipients_for(in_reply_to["url"], actor_url)
                      if in_reply_to and body.visibility == "direct" else
                      [])
        return Note(id=f"{actor_url}/notes/{uuid.uuid4()}",
                    attributedTo=actor_url,
                    content=sanitize_html(body.status),
                    summary=sanitize_html(body.spoiler_text) or None,
                    inReplyTo=in_reply_to["url"] if in_reply_to else None,
                    published=datetime.now(timezone.utc).isoformat(),
                    **({"to": recipients,
                        "tag": list(await asyncio.gather(*(_mention(recipient) for recipient in recipients)))}
                       if in_reply_to and body.visibility == "direct" else
                       {"cc": [in_reply_to["actor_url"]], "tag": [await _mention(in_reply_to["actor_url"])]}
                       if in_reply_to else
                       {}))

    async def make_note_and_create_activity(actor_url, in_reply_to):
        note = await make_note(actor_url, in_reply_to)
        return (note,
                CreateActivity(id=f"{actor_url}#create/{uuid.uuid4()}",
                               actor=actor_url,
                               to=note.to,
                               object=note.model_dump(by_alias=True,
                                                      exclude_none=True)))

    note, activity = \
        await make_note_and_create_activity(actor_url=actor_url_from_username(username),
                                            in_reply_to=await (await as_objects.storage()).get(body.in_reply_to_id, 20)
                                                        if body.in_reply_to_id else
                                                        None)

    async with message_bus().topic("raw_activities").publish() as publish:
        await publish(event_type="Create",
                      object_id=activity.id,
                      payload={"username": username,
                               "activity": {k: v
                                            for k, v in activity.model_dump(by_alias=True,
                                                                            exclude_none=True).items()
                                            if k not in ("id", "type")}})

    resolved = await mentions.resolve_all(note.content, _preliminary_resolver)
    return Status(id=note.id,
                  created_at=note.published,
                  visibility=body.visibility,
                  sensitive=body.sensitive,
                  spoiler_text=note.summary or "",
                  language=body.language,
                  uri=note.id,
                  url=note.id,
                  content=mentions.linkify_resolved(note.content, resolved),
                  mentions=mentions_from_tag(mentions.tag_cc(resolved)[0]),
                  account=await resolve_actor(username))


@router.get("/statuses/{id}")
async def get_status(id: str, claims: Annotated[dict, Depends(current_user)] = None):
    row = await (await as_objects.storage()).get(id, 20) if id.isdigit() else None
    if row is None or row["content"] is None:
        raise HTTPException(status_code=404, detail="status_not_found")
    return (await service.make_statuses([row]))[0]


@router.delete("/statuses/{id}")
async def delete_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")
    actor_url = actor_url_from_username(username)

    url = await (await as_objects.storage()).url_for_author(id, actor_url) if id.isdigit() else None
    if url is None:
        raise HTTPException(status_code=404, detail="status_not_found")

    activity = DeleteActivity(id=f"{actor_url}#delete/{id}",
                              actor=actor_url,
                              object=url)

    async with message_bus().topic("raw_activities").publish() as publish:
        await publish(event_type="Delete",
                      object_id=f"{actor_url}#delete/{id}",
                      payload={"username": username,
                               "activity": activity.as_event_payload()})
    return {}


@router.get("/statuses/{id}/context")
async def status_context(id: str, claims: Annotated[dict, Depends(current_user)] = None):
    if not id.isdigit():
        return StatusContext()
    storage = await as_objects.storage()
    row = await storage.get(id, 20)
    if row is None:
        return StatusContext()

    ancestors = await storage.discussion_ancestors(row["url"])
    descendants = [r for r in await storage.discussion_of(row["url"]) if r["url"] != row["url"]]
    return StatusContext(ancestors=await service.make_statuses(ancestors),
                         descendants=await service.make_statuses(descendants))


@router.post("/statuses/{id}/favourite")
async def favourite_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unfavourite")
async def unfavourite_status(id: str,
                             claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


def _username(claims: dict) -> str:
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    return username


async def _boosted_row(id: str) -> dict:
    row = await (await as_objects.storage()).get(id, 20) if id.isdigit() else None
    if row is None or row["content"] is None:
        raise HTTPException(status_code=404, detail="status_not_found")

    return row


def _boost_state(status: Status, *, reblogged: bool) -> Status:
    status.reblogged = reblogged
    status.reblogs_count = max(status.reblogs_count + (1 if reblogged else -1), 0)

    return status


async def _publish_activity(event_type: str, username: str, activity) -> None:
    async with message_bus().topic("raw_activities").publish() as publish:
        await publish(event_type=event_type,
                      object_id=activity.id,
                      payload={"username": username,
                               "activity": {key: value
                                            for key, value in activity.model_dump(by_alias=True,
                                                                                  exclude_none=True).items()
                                            if key not in ("id", "type")}})


@router.post("/statuses/{id}/reblog")
async def reblog_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    username = _username(claims)
    row = await _boosted_row(id)
    actor_url = actor_url_from_username(username)
    activity = AnnounceActivity(id=f"{actor_url}#announce/{uuid.uuid4()}",
                                actor=actor_url,
                                object=row["url"],
                                published=datetime.now(timezone.utc).isoformat(),
                                to=[_PUBLIC],
                                cc=[f"{actor_url}/followers", row["actor_url"]])
    await _publish_activity("Announce", username, activity)
    return _boost_state((await service.make_statuses([row]))[0], reblogged=True)


@router.post("/statuses/{id}/unreblog")
async def unreblog_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    username = _username(claims)
    row = await _boosted_row(id)
    actor_url = actor_url_from_username(username)
    announce = AnnounceActivity(id=f"{actor_url}#announce/{uuid.uuid4()}",
                                actor=actor_url,
                                object=row["url"])
    await _publish_activity("Undo",
                            username,
                            UndoAnnounceActivity(id=f"{actor_url}#undo/{uuid.uuid4()}",
                                                 actor=actor_url,
                                                 object=announce))
    return _boost_state((await service.make_statuses([row]))[0], reblogged=False)


@router.get("/statuses/{id}/favourited_by")
async def favourited_by(id: str, claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.get("/statuses/{id}/reblogged_by")
async def reblogged_by(id: str, claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.post("/statuses/{id}/bookmark")
async def bookmark_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unbookmark")
async def unbookmark_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/pin")
async def pin_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.post("/statuses/{id}/unpin")
async def unpin_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.put("/statuses/{id}")
async def edit_status(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/statuses/{id}/history")
async def status_history(id: str, claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/statuses/{id}/source")
async def status_source(id: str, claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="status_not_found")


@router.get("/scheduled_statuses")
async def get_scheduled_statuses(claims: Annotated[dict, Depends(current_user)]):
    return []

