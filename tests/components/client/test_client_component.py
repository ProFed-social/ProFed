# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.client import Client, mount_endpoints
from profed.core.component_manager import Component, collect_component_hooks


async def test_entry_is_a_no_op():
    assert await Client({}) is None


async def test_mount_endpoints_is_a_callable_no_op():
    assert await mount_endpoints(object(), {}) is None


def test_component_resolves_the_entry_without_db_schema():
    component = Component("client")
    assert component.entry is Client
    assert component.using_schemata == []


def test_mount_endpoints_is_collected_as_a_hook():
    hooks = collect_component_hooks(["client"], "mount_endpoints")
    assert hooks["client"] is mount_endpoints

