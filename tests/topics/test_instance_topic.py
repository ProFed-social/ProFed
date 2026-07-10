# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.topics.instance_topic import (validate_instance_event,
                                          validate_instance_snapshot_item)
 
 
PAYLOAD = {"public_key_pem": "PUB",
           "private_key_pem": "PRIV",
           "preferredUsername": "example.com",
           "name": "Example",
           "summary": "An instance",
           "icon": "https://example.com/icon.png",
           "image": "https://example.com/image.png"}
 
 
def test_valid_set_event_returns_payload():
    payload = validate_instance_event("set", PAYLOAD)
 
    assert payload is not None
    assert payload["public_key_pem"] == "PUB"
 
 
def test_non_set_event_is_rejected():
    assert validate_instance_event("created", PAYLOAD) is None
 
 
def test_non_dict_payload_returns_none():
    assert validate_instance_event("set", "x") is None
 
 
def test_missing_key_material_returns_none():
    assert validate_instance_event("set", {"name": "Example"}) is None
 
 
def test_valid_snapshot_item_returns_item():
    assert validate_instance_snapshot_item(PAYLOAD) == PAYLOAD
 
 
def test_non_dict_snapshot_item_returns_none():
    assert validate_instance_snapshot_item("x") is None
 
