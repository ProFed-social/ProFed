# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.topics.common import MeLinkEvent, validate_payload, validate_verb


CHECK_STATES = {"verified", "unverified", "gone"}

ME_LINK_STATES = CHECK_STATES | {"deleted"}


def link_id(profile_url: str, link_url: str) -> str:
    return f"{profile_url}|{link_url}"


def link_parts(object_id: str) -> tuple[str, str]:
    return object_id.split("|", 1)


def validate_me_links_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if not validate_verb(event_type, ME_LINK_STATES, "me_links"):
        return None

    return payload if event_type == "deleted" else validate_payload(MeLinkEvent, payload, "me_links")


def validate_me_links_snapshot_item(item) -> Optional[Dict]:
    return validate_payload(MeLinkEvent, item, "me_links")


topic = {"name": "me_links",
         "validate": validate_me_links_event,
         "snapshot_validate": validate_me_links_snapshot_item}

