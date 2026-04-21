# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import secrets
from fastapi import APIRouter
from pydantic import BaseModel
from profed.core.message_bus import message_bus
 
 
router = APIRouter()


active = False
 
 
def init(config: dict) -> None:
    global active
    active = True 


class AppRegistration(BaseModel):
    client_name: str
    redirect_uris: str
    scopes: str = "read"
    website: str = ""
 
 
@router.post("/api/v1/apps")
async def register_app(body: AppRegistration):
    client_id     = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(32)
 
    async with message_bus().topic("oauth_apps").publish() as publish:
        await publish({"type": "created",
                       "payload": {"client_id":     client_id,
                                   "client_secret": client_secret,
                                   "client_name":   body.client_name,
                                   "redirect_uris": body.redirect_uris,
                                   "scopes":        body.scopes}})
 
    return {"id":           client_id,
            "client_id":     client_id,
            "client_secret": client_secret,
            "name":          body.client_name,
            "redirect_uri":  body.redirect_uris,
            "scopes":        body.scopes,
            "website":       body.website}

