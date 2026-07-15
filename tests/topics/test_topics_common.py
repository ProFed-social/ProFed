# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from pydantic import BaseModel

from profed.topics.common import ActivityEvent, validate_payload, validate_verb


class _Model(BaseModel):
    name: str
    note: Optional[str] = None


def test_validate_verb_accepts_known_verb():
    assert validate_verb("Create", {"Create", "Update"}, "demo") is True


def test_validate_verb_rejects_unknown_verb():
    assert validate_verb("Tick", {"Create", "Update"}, "demo") is False


def test_validate_payload_returns_dumped_model():
    assert validate_payload(_Model, {"name": "alice"}, "demo") == {"name": "alice", "note": None}


def test_validate_payload_can_exclude_none():
    assert validate_payload(_Model, {"name": "alice"}, "demo", exclude_none=True) == {"name": "alice"}


def test_validate_payload_rejects_invalid_payload():
    assert validate_payload(_Model, {"note": "no name"}, "demo") is None


def test_validate_payload_rejects_non_dict():
    assert validate_payload(_Model, "nope", "demo") is None


def test_activity_event_keeps_payload_unchanged():
    payload = {"username": "alice", "activity": {"actor": "https://remote/bob"}}

    assert validate_payload(ActivityEvent, payload, "demo") == payload


def test_activity_event_keeps_extra_fields():
    payload = {"username": "alice", "activity": {}, "origin": "https://remote", "maybe": None}

    assert validate_payload(ActivityEvent, payload, "demo") == payload


def test_activity_event_requires_non_empty_username():
    assert validate_payload(ActivityEvent, {"username": "", "activity": {}}, "demo") is None


def test_activity_event_requires_activity_dict():
    assert validate_payload(ActivityEvent, {"username": "alice", "activity": "nope"}, "demo") is None

