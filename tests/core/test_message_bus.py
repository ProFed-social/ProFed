# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
from typing import Dict
from types import ModuleType
import asyncio

from pytest import fixture

from profed.core.config import config, raw

import profed.core.message_bus as message_bus

class Cfg:
    def __init__(self, config: Dict[str, Dict[str, str]]):
        raw.paths = []
        raw.argv = [""] + [f"--{section}.{parameter}={value}"
                           for section, s in config.items()
                           for parameter, value in s.items()]
        os.environ = {var: val
                      for var, val in os.environ.items()
                      if not var.startswith("PROFED_")}

    def __enter__(self):
        config.reset()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val


@fixture
def mock_module():
    mod = ModuleType("profed.core.message_bus.example")
    sys.modules["profed.core.message_bus.example"] = mod
    exec("def init(cfg):\n"
         "    return cfg\n",
         mod.__dict__)


def test_message_bus_isntantiation(mock_module):
    with Cfg({"message_bus": {"type": "example"}, "profed": {"run":""}}):
        message_bus._instance = None
        message_bus.init_message_bus()

        bus = message_bus.message_bus()

        assert type(bus) == dict
        assert bus["type"] == "example"


def test_message_bus_fail_without_init(mock_module):
    with Cfg({"message_bus": {"type": "example"}, "profed": {"run":""}}):
        message_bus._instance = None

        try:
            message_bus.message_bus()
            assert False, "expected RuntimeError - got no Exception"
        except RuntimeError:
            pass
        except Exception as e:
            assert False, f"expected RuntimeError - got different Exception: {e}"

