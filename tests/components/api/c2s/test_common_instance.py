# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import os
from profed.core.config import config, raw
from profed.components.api.c2s.common.instance import build_common_response
 
 
class Cfg:
    def __init__(self, cfg):
        raw.paths = []
        raw.argv = [""] + [f"--{s}.{k}={v}"
                            for s, d in cfg.items()
                            for k, v in d.items()]
        os.environ = {k: v for k, v in os.environ.items()
                      if not k.startswith("PROFED_")}
 
    def __enter__(self):
        config.reset()
 
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val
 
 
def test_build_common_response_contains_title():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({"title": "My ProFed"}, "example.com", 5000)
    assert result["title"] == "My ProFed"
 
 
def test_build_common_response_max_characters():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 3000)
    assert result["configuration"]["statuses"]["max_characters"] == 3000
 
 
def test_build_common_response_default_title_is_domain():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)
    assert result["title"] == "example.com"
