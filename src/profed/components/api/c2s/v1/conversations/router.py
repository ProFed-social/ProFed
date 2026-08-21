# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from fastapi import APIRouter, Depends
from typing import Annotated
from profed.identity import actor_url_from_username
from profed.models.mastodon import Account, Conversation, placeholder_account
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
        async def resolve(actor_url):
            entry = await accounts.get_by_actor_url(actor_url)
            return Account.model_validate(entry["account"]) if entry else placeholder_account(actor_url)
        return await asyncio.gather(*(resolve(actor_url) for actor_url in actor_urls))

    return [Conversation(id=roots.get(row["conversation_id"], row["conversation_id"]),
                         accounts=await accounts_of(row["accounts"]),
                         last_status=last_status.get(row["last_message"]))
            for row in rows]


@router.get("/conversations/{id}/messages")
async def conversation_messages(id: str, claims: Annotated[dict, Depends(current_user)]):
    conversation_id = await (await as_objects.storage()).url_for(id) or id
    return await service.make_statuses(await (await conversations.storage()).messages_of(conversation_id))

