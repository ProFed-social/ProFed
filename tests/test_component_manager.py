# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from types import ModuleType
from pytest import fixture

from profed.core.component_manager import run, Component, Process

@fixture
def mock_module():
    mod = ModuleType("profed.adapters.example")
    sys.modules["profed.adapters.example"] = mod
    exec("async def Example(cfg):\n"
         "    assert(cfg[\"foo\"] == \"bar\")\n",
         mod.__dict__)


def test_component_manager_with_main(mock_module):
    run({"example": {"foo": "bar"}}, "example")


def test_component_manager_without_main(mock_module):
    run({"example": {"foo": "bar"}})


def test_component(mock_module):
    cmp = Component("example")
    cmp({"foo": "bar"})


def test_process(mock_module):
    p = Process(Component("example"), {"foo": "bar"})
    p.wait()


