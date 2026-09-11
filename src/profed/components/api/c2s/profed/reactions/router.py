# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Annotated
from fastapi import APIRouter, Depends

from profed.identity import actor_url_from_username
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.statuses import as_objects


router = APIRouter()
active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/reactions/history")
async def history(claims: Annotated[dict, Depends(current_user)]) -> dict:
    username = claims.get("preferred_username") or claims.get("sub")
    store = await as_objects.storage()
    actor_url = actor_url_from_username(username)

    return {"counts": await store.reaction_counts_of(actor_url),
            "last_toned": await store.last_toned_reaction_of(actor_url)}

