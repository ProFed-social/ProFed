# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends
from typing import Annotated
from profed.identity import actor_url_from_username
from profed.models.mastodon import Account, Conversation
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.conversations import storage as conversations
from profed.components.api.c2s.shared.known_accounts import storage as known_accounts
from profed.components.api.c2s.shared.statuses import as_objects
from profed.components.api.c2s.shared.statuses import service


router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/conversations")
async def get_conversations(claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    rows = await (await conversations.storage()).conversations_of(actor_url_from_username(username))
    if not rows:
        return []

    objects = await as_objects.storage()
    accounts = await known_accounts.storage()
    last_status = {status.url: status
                   for status in await service.make_statuses(
                       await objects.rows_for_urls([row["last_message"] for row in rows], 20))}
    roots = await objects.mastodon_ids_for([row["conversation_id"] for row in rows])

    async def accounts_of(actor_urls):
        known = [await accounts.get_by_actor_url(actor) for actor in actor_urls]
        return [Account.model_validate(entry["account"]) for entry in known if entry is not None]

    return [Conversation(id=roots.get(row["conversation_id"], row["conversation_id"]),
                         accounts=await accounts_of(row["accounts"]),
                         last_status=last_status.get(row["last_message"]))
            for row in rows]

