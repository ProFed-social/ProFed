# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import configparser
import os
import sys
import re
from pathlib import Path
from typing import Dict
from collections.abc import Sequence


paths = [Path("/etc/profed.ini"),
         Path.home() / ".config/profed.ini",
         Path.cwd() / "profed.ini"]
env_prefix = "PROFED_"
argv = sys.argv


_raw_conf_t = Dict[str, Dict[str, str]]

def update_raw(raw: _raw_conf_t, upd: _raw_conf_t) -> _raw_conf_t:
    for section, new_values in upd.items():
        raw.setdefault(section, {}).update(new_values)
    return raw
    

def files(paths: Sequence[Path]) -> _raw_conf_t:
    cp = configparser.ConfigParser()
    cp.read(paths)
    return {section: dict(cp.items(section)) for section in cp.sections()}


def env(env_prefix: str, raw: _raw_conf_t) -> _raw_conf_t:
    upd: _raw_conf_t  = {}
    for k, v in os.environ.items():
        if k.startswith(env_prefix):
            section, param = k[len(env_prefix):].lower().split("__", 1)
            upd.setdefault(section, {})[param] = v
    return update_raw(raw, upd)


def cli(argv: Sequence[str], raw: _raw_conf_t) -> _raw_conf_t:
    rx = re.compile("--([^.)]*)[.]([^.=]*)=(.*)")

    upd = {}
    for arg in argv[1:]:
        print(arg)
        m = rx.fullmatch(arg)
        if m:
            section, param, value = m.group(1, 2, 3)
            print(section, param, value)
            upd.setdefault(section, {})[param] = value

    return update_raw(raw, upd)



_raw = None

def raw_config() -> _raw_conf_t:
    global _raw, paths, env_prefix, argv

    if _raw is None:
        _raw = files(paths)
        _raw = env(env_prefix, _raw)
        _raw = cli(argv, _raw)

    return _raw

def force_reload_raw():
    global _raw
    _raw = None

    return raw_config()
