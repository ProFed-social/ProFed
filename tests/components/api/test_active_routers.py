# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.components.api.active_routers import (narrow_deactivate_routers,
                                                    get_active)
 
 
def test_narrow_deactivate_routers_filters_by_prefix():
    result = narrow_deactivate_routers("v1_", ["v1_accounts", "v2_instance", "v1_statuses"])
    assert result == ["accounts", "statuses"]
 
 
def test_narrow_deactivate_routers_empty_list():
    assert narrow_deactivate_routers("v1_", []) == []
 
 
def test_narrow_deactivate_routers_no_match():
    assert narrow_deactivate_routers("v1_", ["v2_instance", "oauth"]) == []
 
 
def test_get_active_excludes_deactivated():
    items = {"accounts": "a", "statuses": "b", "timelines": "c"}
    result = get_active(items, ["statuses"])
    assert result == ["a", "c"]
 
 
def test_get_active_empty_deactivate():
    items = {"accounts": "a", "statuses": "b"}
    result = get_active(items, [])
    assert result == ["a", "b"]
 
 
def test_get_active_all_deactivated():
    items = {"accounts": "a", "statuses": "b"}
    result = get_active(items, ["accounts", "statuses"])
    assert result == []

