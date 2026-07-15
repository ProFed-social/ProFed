# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends
from typing import Annotated
from profed.components.api.c2s.shared.auth import current_user
from profed.identity import domain
from profed.components.api.c2s.shared.instance import build_common_response


router = APIRouter()
active = False
_config: dict = {}


def init(config: dict) -> None:
    global active, _config
    active = True
    _config = config


@router.get("/instance")
async def instance():
    d = domain()
    max_chars = int(_config.get("status_max_characters", 5000))
    return  dict(build_common_response(_config, d, max_chars),
                 uri=d,
                 short_description=_config.get("description", ""),
                 email=_config.get("admin_email", ""),
                 urls={},
                 stats={"user_count":   0,
                        "status_count": 0,
                        "domain_count": 0},
                 registrations=False,
                 approval_required=False,
                 invites_enabled=False)


@router.get("/custom_emojis")
async def custom_emojis():
    return []


@router.get("/announcements")
async def announcements():
    return []


@router.get("/instance/peers")
async def instance_peers():
    return []


@router.get("/instance/rules")
async def instance_rules():
    return []


@router.get("/instance/activity")
async def instance_activity():
    return []

