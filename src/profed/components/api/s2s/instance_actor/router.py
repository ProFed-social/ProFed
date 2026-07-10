# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, HTTPException
from profed.identity import domain
from profed.models.activity_pub.application import Application
from profed.components.api.http import ActivityPubJSONResponse
from profed.components.api.s2s.instance_actor.projection import current

router = APIRouter()


@router.get("/actor", response_model=Application, response_class=ActivityPubJSONResponse)
async def instance_actor():
    state = current()
    if not state:
        raise HTTPException(status_code=404)
    return Application.from_state(state, f"https://{domain()}/actor")

