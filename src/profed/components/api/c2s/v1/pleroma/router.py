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


def _without_own(reactions: list[dict]) -> list[dict]:
    return [entry
            for entry in ({**entry, "count": entry["count"] - 1, "me": False} if entry["me"] else entry
                          for entry in reactions)
            if entry["count"] > 0]


def _with_own(reactions: list[dict], emoji: str) -> list[dict]:
    without = _without_own(reactions)

    return [*(entry for entry in without if entry["name"] != emoji),
            {"name": emoji,
             "count": next((entry for entry in without if entry["name"] == emoji), {"count": 0})["count"] + 1,
             "me": True}]


def _breakdown(status: Status, reactions: list[dict]) -> Status:
    content = status.reblog or status
    content.pleroma = {**(status.reblog or status).pleroma, "emoji_reactions": reactions}

    return status


def _reacted(status: Status, emoji: str) -> Status:
    content = status.reblog or status
    reactions = (content.pleroma.get("emoji_reactions", [])
                 if any(entry["me"] and entry["name"] == emoji
                        for entry in content.pleroma.get("emoji_reactions", [])) else
                 _with_own(content.pleroma.get("emoji_reactions", []), emoji))

    return _reaction_state(_breakdown(status, reactions), favourited=True)


def _unreacted(status: Status) -> Status:
    return _reaction_state(_breakdown(status,
                                      _without_own((status.reblog or status).pleroma.get("emoji_reactions", []))),
                           favourited=False)


async def _undo_like(username: str, actor_url: str, row: dict, like_url: str) -> None:
    await _publish_activity("Undo",
                            username,
                            UndoLikeActivity(id=f"{actor_url}#undo/{uuid.uuid4()}",
                                             actor=actor_url,
                                             to=[row["content"]["actor"]],
                                             object=LikeActivity(id=like_url,
                                                                 actor=actor_url,
                                                                 object=row["content"]["url"])))



@router.put("/pleroma/statuses/{id}/reactions/{emoji}")
async def react(id: str, emoji: str, claims: Annotated[dict, Depends(current_user)]) -> Status:
    async def publish_undo(username, row, actor_url, own):
        if own is not None and own["emoji"] != emoji:
            await _undo_like(username, actor_url, row, own["reaction_url"])

    async def publish_like(username, row, actor_url, own):
        if own is None or own["emoji"] != emoji:
            await _publish_activity("Like",
                                    username,
                                    LikeActivity(id=f"{actor_url}#like/{uuid.uuid4()}",
                                                 actor=actor_url,
                                                 object=row["content"]["url"],
                                                 content=emoji,
                                                 published=datetime.now(timezone.utc).isoformat(),
                                                 to=[row["content"]["actor"]],
                                                 **{"_misskey_reaction": emoji}))

    async def publish_events(username, row, actor_url, own):
        await publish_undo(username, row, actor_url, own)
        await publish_like(username, row, actor_url, own)

        return [row], actor_url

    async def reaction_events(username, row, actor_url):
        return await publish_events(username,
                                    row,
                                    actor_url,
                                    own=await (await as_objects.storage()).own_reaction(actor_url,
                                                                                        row["content"]["url"]))

    async def do_react(username, row):
        return await reaction_events(username, row, actor_url_from_username(username))

    return _reacted((await service.make_statuses(*(await do_react(username=_username(claims),
                                                                  row=await _boosted_row(id)))))[0],
                    emoji)


@router.delete("/pleroma/statuses/{id}/reactions/{emoji}")
async def unreact(id: str, emoji: str, claims: Annotated[dict, Depends(current_user)]) -> Status:
    async def do_publish_undo(username, row, actor_url, own):
        if own is not None:
            await _undo_like(username, actor_url, row, own["reaction_url"])

    async def publish_undo(username, row, actor_url):
        await do_publish_undo(username,
                              row,
                              actor_url,
                              own=await (await as_objects.storage()).own_reaction(actor_url, row["content"]["url"]))
   
        return [row], actor_url

    async def do_unreact(username, row):
        return await publish_undo(username, row, actor_url=actor_url_from_username(username))


    return _unreacted((await service.make_statuses(*(await do_unreact(username=_username(claims),
                                                                      row=await _boosted_row(id)))))[0])

