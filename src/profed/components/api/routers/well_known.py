# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, HTTPException, Query
from profed.components.api.services.webfinger import (resolve_actor_url,
                                                      resolve_acct_from_actor_url)


router = APIRouter()


@router.get("/.well-known/webfinger")
async def webfinger(resource: str = Query(pattern=r"^(acct:[^@]+@[^@]+|https?://.+)$")):
    acct = (resource[len("acct:"):]
            if resource.startswith("acct:") else
            await resolve_acct_from_actor_url(resource))
    if acct is None:
        raise HTTPException(status_code=404)

    try:
        actor_url = await resolve_actor_url(acct)
        if actor_url is None:
            raise HTTPException(status_code=404)

        return ({"subject": f"acct:{acct}",
                 "links": [{"rel": "self",
                            "type": "application/activity+json",
                            "href": actor_url}]}
                if actor_url is not None else None)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500)

