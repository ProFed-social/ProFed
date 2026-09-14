# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Optional
from urllib.parse import urlsplit

from profed.topics.common import (ServerObservationEvent,
                                  ServerUpdateEvent,
                                  validate_payload,
                                  validate_verb)


DEFAULT_PORTS = {"http": "80", "https": "443"}

PAYLOAD_MODELS = {"observed": ServerObservationEvent, "updated": ServerUpdateEvent}

KNOWN_SERVER_STATES = {"discovered", "lost"} | set(PAYLOAD_MODELS)


def _split(url: str):
    return urlsplit(url if "//" in url else f"//{url}")


def _bracketed(host: str) -> str:
    return f"[{host}]" if ":" in host else host


def _authority(scheme: str, host: str, port: Optional[int]) -> str:
    return (_bracketed(host)
            if port is None or DEFAULT_PORTS.get(scheme) == str(port) else
            f"{_bracketed(host)}:{port}")


def host_of(url: str) -> str:
    parts = _split((url or "").strip())
    try:
        host, port = parts.hostname or "", parts.port
    except ValueError:
        return ""

    return "" if not host or any(char.isspace() for char in host) else _authority(parts.scheme, host, port)


def validate_known_servers_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if not validate_verb(event_type, KNOWN_SERVER_STATES, "known_servers"):
        return None

    model = PAYLOAD_MODELS.get(event_type)
    return payload if model is None else validate_payload(model, payload, "known_servers")


def validate_known_servers_snapshot_item(item) -> Optional[Dict]:
    return validate_payload(ServerUpdateEvent, item, "known_servers")


topic = {"name": "known_servers",
         "validate": validate_known_servers_event,
         "snapshot_validate": validate_known_servers_snapshot_item}

