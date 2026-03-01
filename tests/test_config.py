# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
from types import ModuleType
import profed.core.config.raw as raw
from profed.core.config import config 



class Cfg:
    def __init__(self, tmp_path=None, files=None, argv=None, env=None):
        self.tmp_path = tmp_path
        self.files = files or []
        raw.paths = []
        raw.argv = argv or []
        os.environ = env or {}

    def __enter__(self):
        for name, content in self.files:
            f = self.tmp_path / name
            f.write_text(content)
            raw.paths.append(f)

        config.reset()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for f in raw.paths:
            f.unlink()


def test_simple_config_file(tmp_path):
    with Cfg(tmp_path, files=[("config.ini", "[profed]\nrun=example\n[example]\nfoo=bar\n")]):
        assert config()["example"]["foo"] == "bar"


def test_environment():
    with Cfg(env={"PROFED_EXAMPLE__FOO": "bar", "PROFED_PROFED__RUN": "example"}):
        assert config()["example"]["foo"] == "bar"


def test_command_line():
    with Cfg(argv=["", "--example.foo=bar", "--profed.run=example"]):
        assert config()["example"]["foo"] == "bar"


def test_files_override(tmp_path):
    with Cfg(tmp_path, files=[("config1.ini", "[example]\nfoo=bar\n"),
                              ("config2.ini", "[profed]\nrun=example\n[example]\nfoo=blub\n")]):
        assert config()["example"]["foo"] == "blub"


def test_environment_override_file(tmp_path):
    with Cfg(tmp_path,
             files=[("config.ini", "[profed]\nrun=example\n[example]\nfoo=bar\n")],
             env={"PROFED_EXAMPLE__FOO": "blub"}):
        assert config()["example"]["foo"] == "blub"


def test_command_line_override_file(tmp_path):
    with Cfg(tmp_path,
             files=[("config.ini", "[profed]\nrun=example\n[example]\nfoo=bar\n")],
             argv = ["", "--example.foo=blub"]):
        assert config()["example"]["foo"] == "blub"


def test_command_line_override_environment():
    with Cfg(env={"PROFED_EXAMPLE__FOO": "bar", "PROFED_PROFED__RUN": "example"},
             argv = ["", "--example.foo=blub"]):
        assert config()["example"]["foo"] == "blub"


def test_component_parser():
    mod = ModuleType("profed.adapters.example.config")
    sys.modules["profed.adapters.example.config"] = mod
    exec("def parse(cfg):\n"
         "    cfg['foo'] = \"blub\"\n"
         "    return cfg\n",
         mod.__dict__)

    with Cfg(argv = ["", "--example.foo=bar", "--profed.run=example"]):
        assert config()["example"]["foo"] == "blub"


