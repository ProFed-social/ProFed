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
    return _reaction_state((await service.make_statuses([row], actor_url))[0], favourited=True)


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
                                                 object=LikeActivity(id=like_url,
                                                                     actor=actor_url,
                                                                     object=row["content"]["url"])))
    return _reaction_state((await service.make_statuses([row], actor_url))[0], favourited=False)

