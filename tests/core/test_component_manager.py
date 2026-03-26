# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from types import ModuleType
from pytest import fixture, mark

from profed.core.component_manager import run, Component

@fixture
def mock_module():
    mod = ModuleType("profed.components.example")
    sys.modules["profed.components.example"] = mod
    exec("async def Example(cfg):\n"
         "    assert(cfg[\"foo\"] == \"bar\")\n",
         mod.__dict__)


def test_component_manager_with_main(mock_module):
    run({"example": {"foo": "bar"}, "profed": {"run": "example"}})


def test_component_manager_without_main(mock_module):
    run({"example": {"foo": "bar"}, "profed": {"run": "example"}})


@mark.asyncio
async def test_component(mock_module):
    cmp = Component("example")
    await cmp({"foo": "bar"})

