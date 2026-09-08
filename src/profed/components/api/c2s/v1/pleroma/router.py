# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends

from profed.identity import actor_url_from_username
from profed.models.activity_pub import LikeActivity, UndoLikeActivity
from profed.models.mastodon import Status
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.statuses import as_objects, service
from profed.components.api.c2s.v1.statuses.router import (_boosted_row,
                                                          _publish_activity,
                                                          _reaction_state,
                                                          _username)

router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


def _reacted(status: Status, emoji: str) -> Status:
    content = status.reblog or status
    if not any(entry["me"] for entry in content.pleroma.get("emoji_reactions", [])):
        content.pleroma = {**content.pleroma,
                           "emoji_reactions": _with_own(content.pleroma.get("emoji_reactions", []), emoji)}

    return _reaction_state(status, favourited=True)

def _with_own(reactions: list[dict], emoji: str) -> list[dict]:
    others = [entry for entry in reactions if entry["name"] != emoji]
    mine = next((entry for entry in reactions if entry["name"] == emoji), {"name": emoji, "count": 0, "me": False})

    return [*others, {"name": emoji, "count": mine["count"] + 1, "me": True}]

def _unreacted(status: Status) -> Status:
    content = status.reblog or status
    remaining = [{**entry, "count": entry["count"] - 1, "me": False} if entry["me"] else entry
                 for entry in content.pleroma.get("emoji_reactions", [])]
    content.pleroma = {**content.pleroma, "emoji_reactions": [e for e in remaining if e["count"] > 0]}

    return _reaction_state(status, favourited=False)



@router.put("/pleroma/statuses/{id}/reactions/{emoji}")
async def react(id: str, emoji: str, claims: Annotated[dict, Depends(current_user)]) -> Status:
    username = _username(claims)
    row = await _boosted_row(id)
    actor_url = actor_url_from_username(username)
    if await (await as_objects.storage()).reaction_of(actor_url, row["content"]["url"]) is None:
        await _publish_activity("Like",
                                username,
                                LikeActivity(id=f"{actor_url}#like/{uuid.uuid4()}",
                                             actor=actor_url,
                                             object=row["content"]["url"],
                                             content=emoji,
                                             published=datetime.now(timezone.utc).isoformat(),
                                             to=[row["content"]["actor"]],
                                             **{"_misskey_reaction": emoji}))
    return _reacted((await service.make_statuses([row], actor_url))[0], emoji)


@router.delete("/pleroma/statuses/{id}/reactions/{emoji}")
async def unreact(id: str, emoji: str, claims: Annotated[dict, Depends(current_user)]) -> Status:
    username = _username(claims)
    row = await _boosted_row(id)
    actor_url = actor_url_from_username(username)
    like_url = await (await as_objects.storage()).reaction_of(actor_url, row["content"]["url"])
    if like_url is not None:
        await _publish_activity("Undo",
                                username,
                                UndoLikeActivity(id=f"{actor_url}#undo/{uuid.uuid4()}",
                                                 actor=actor_url,
                                                 to=[row["content"]["actor"]],
                                                 object=LikeActivity(id=like_url,
                                                                     actor=actor_url,
                                                                     object=row["content"]["url"])))
    return _unreacted((await service.make_statuses([row], actor_url))[0])

