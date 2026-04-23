# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core.config import config, raw
from profed.components.api.s2s.nodeinfo.router import router


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
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_well_known_nodeinfo_returns_link(client):
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        response = client.get("/.well-known/nodeinfo")

    assert response.status_code == 200
    data = response.json()
    assert len(data["links"]) == 1
    assert data["links"][0]["href"] == "https://example.com/nodeinfo/2.0"
    assert "nodeinfo.diaspora.software" in data["links"][0]["rel"]


def test_nodeinfo_returns_activitypub_protocol(client):
    response = client.get("/nodeinfo/2.0")

    assert response.status_code == 200
    assert "activitypub" in response.json()["protocols"]


def test_nodeinfo_returns_correct_software_name(client):
    response = client.get("/nodeinfo/2.0")

    assert response.json()["software"]["name"] == "profed"


def test_nodeinfo_content_type(client):
    response = client.get("/nodeinfo/2.0")

    assert "nodeinfo.diaspora.software" in response.headers["content-type"]

