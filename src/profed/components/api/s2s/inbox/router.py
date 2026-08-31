# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from fastapi import APIRouter, HTTPException, Path, Request, Response
from profed.components.api.s2s.inbox.service import accept_inbox_activity, verify_inbox_request

logger = logging.getLogger(__name__)
router = APIRouter()


async def _verified_activity(request: Request) -> dict:
    body = await request.body()
    if not await verify_inbox_request(request.method, request.url.path, dict(request.headers), body):
        raise HTTPException(status_code=401)
    return json.loads(body)


@router.post("/actors/{username}/inbox")
async def inbox(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$"), request: Request = None):
    try:
        activity = await _verified_activity(request)
        if not await accept_inbox_activity(username, activity):
            raise HTTPException(status_code=404)

        return Response(status_code=202)

    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400)


@router.post("/actor/inbox")
async def instance_inbox(request: Request = None):
    try:
        activity = await _verified_activity(request)
        logger.info("instance inbox: discarding %s from %s", activity.get("type"), activity.get("actor"))

        return Response(status_code=202)

    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400)


