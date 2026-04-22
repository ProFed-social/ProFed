# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter
from profed.identity import domain
from profed.components.api.c2s.common.instance import build_common_response
 
 
router = APIRouter()
active = False
_config: dict = {}
 
 
def init(config: dict) -> None:
    global active, _config
    active = True
    _config = config
 
 
@router.get("/instance")
async def instance_v2():
    d = domain()
    max_chars = int(_config.get("status_max_characters", 5000))
    return  dict(build_common_response(_config, d, max_chars),
                 domain=d,
                 source_url="https://codeberg.org/ProFed/ProFed",
                 description=_config.get("description", ""),
                 usage={"users": {"active_month": 0}},
                 thumbnail={"url": ""},
                 rules=[],
                 registrations={"enabled": False,
                                "approval_required": False,
                                "message": None},
                 contact={"email": _config.get("admin_email", ""),
                          "account": None},
                 api_versions={"mastodon": 1})

