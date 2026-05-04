# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from fastapi import APIRouter, HTTPException, Path, Request, Response
from profed.components.api.s2s.inbox.service import accept_inbox_activity, verify_inbox_request

router = APIRouter()


@router.post("/actors/{username}/inbox")
async def inbox(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$"), request: Request = None):
    try:
        body = await request.body()
        if not await verify_inbox_request(request.method,
                                          request.url.path,
                                          dict(request.headers),
                                          body):
            raise HTTPException(status_code=401)

        activity = json.loads(body)
        accepted = await accept_inbox_activity(username, activity)
        if not accepted:
            raise HTTPException(status_code=404)

        return Response(status_code=202)

    except HTTPException:
        raise
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=400)
    except Exception:
        raise HTTPException(status_code=500)

