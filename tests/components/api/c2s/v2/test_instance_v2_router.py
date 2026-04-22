# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core.config import config, raw
from profed.components.api.c2s.v2.instance import router as instance_v2_module
 
 
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
 
 
@pytest.fixture
def client():
    instance_v2_module.init({"status_max_characters": "5000",
                             "title":                "Test ProFed"})
    app = FastAPI()
    app.include_router(instance_v2_module.router)
    return TestClient(app)
 
 
def test_instance_v2_returns_domain(client):
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        response = client.get("/instance")
    assert response.status_code == 200
    assert response.json()["domain"] == "example.com"
 
 
def test_instance_v2_returns_mastodon_api_version(client):
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        response = client.get("/instance")
    assert response.json()["api_versions"]["mastodon"] == 1
 
 
def test_instance_v2_active_flag_set_after_init():
    instance_v2_module.init({})
    assert instance_v2_module.active is True

