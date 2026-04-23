# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from profed.identity import domain
 
 
router = APIRouter()
 
 
@router.get("/.well-known/nodeinfo")
async def well_known_nodeinfo():
    d = domain()
    return {"links": [{"rel":  "http://nodeinfo.diaspora.software/ns/schema/2.0",
                        "href": f"https://{d}/nodeinfo/2.0"}]}
 
 
@router.get("/nodeinfo/2.0")
async def nodeinfo():
    return JSONResponse(content={"version": "2.0",
                                 "software": {"name": "profed",
                                              "version": "0.1.0"},
                                 "protocols": ["activitypub"],
                                 "usage": {"users": {"total": 0,
                                                     "activeMonth": 0,
                                                     "activeHalfyear": 0},
                                           "localPosts": 0},
                                 "openRegistrations": False},
                        media_type="application/json; profile=\"http://nodeinfo.diaspora.software/ns/schema/2.0#\"")


