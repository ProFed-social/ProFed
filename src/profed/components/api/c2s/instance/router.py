# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter
from profed.identity import domain
 
 
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
    return {"uri":               d,
            "title":             _config.get("title", d),
            "description":       _config.get("description", ""),
            "short_description": _config.get("description", ""),
            "email":             _config.get("admin_email", ""),
            "version":           "0.1.0 (compatible; ProFed 0.1.0)",
            "urls":              {},
            "stats":             {"user_count":   0,
                                  "status_count": 0,
                                  "domain_count": 0},
            "languages":         ["en"],
            "registrations":     False,
            "approval_required": False,
            "invites_enabled":   False,
            "configuration":     {"statuses":          {"max_characters":       max_chars,
                                                        "max_media_attachments": 0},
                                  "accounts":          {"max_featured_tags": 0},
                                  "media_attachments": {"supported_mime_types":   [],
                                                        "image_size_limit":        0,
                                                        "image_matrix_limit":      0,
                                                        "video_size_limit":        0,
                                                        "video_frame_rate_limit":  0,
                                                        "video_matrix_limit":      0},
                                  "polls":             {"max_options":             0,
                                                        "max_characters_per_option": 0,
                                                        "min_expiration":           0,
                                                        "max_expiration":           0}}}

