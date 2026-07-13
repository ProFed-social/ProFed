# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from pydantic import TypeAdapter, ValidationError
from profed.models.activity_pub import IncomingActivity
from profed.models.activity_pub.fields import ActivityType, ActorRef


def test_activity_type_from_string():
    assert TypeAdapter(ActivityType).validate_python("Follow") == "Follow"


def test_activity_type_from_list_takes_first_string():
    assert TypeAdapter(ActivityType).validate_python(["Follow"]) == "Follow"


def test_activity_type_from_list_skips_empty_strings():
    assert TypeAdapter(ActivityType).validate_python(["", "Create"]) == "Create"


def test_actor_ref_from_string():
    assert TypeAdapter(ActorRef).validate_python("https://r.example/a") == "https://r.example/a"


def test_actor_ref_from_object_takes_id():
    assert TypeAdapter(ActorRef).validate_python({"id":   "https://r.example/a",
                                                  "type": "Person"}) == "https://r.example/a"


def test_incoming_activity_normalizes_type_and_actor():
    activity = IncomingActivity.model_validate({"id":    "https://r.example/act/1",
                                                "type":  ["Follow"],
                                                "actor": {"id": "https://r.example/a"}})
    assert activity.type == "Follow"
    assert activity.actor == "https://r.example/a"


def test_incoming_activity_passes_extras_through():
    activity = IncomingActivity.model_validate({"id":     "x",
                                                "type":   "Create",
                                                "actor":  "https://r.example/a",
                                                "object": {"type": "Note", "content": "hi"}})
    assert activity.model_dump()["object"] == {"type": "Note", "content": "hi"}


def test_incoming_activity_requires_id():
    with pytest.raises(ValidationError):
        IncomingActivity.model_validate({"type": "Follow", "actor": "https://r.example/a"})


def test_incoming_activity_rejects_empty_type():
    with pytest.raises(ValidationError):
        IncomingActivity.model_validate({"id": "x", "type": "", "actor": "https://r.example/a"})

