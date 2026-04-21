# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import os
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core.config import config, raw
from profed.components.api.c2s.accounts import router as accounts_module
from profed.components.api.c2s.auth import current_user 
 
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
 
 
CLAIMS = {"preferred_username": "alice", "sub": "alice"}
 
 
class FakePerson:
    name = "Alice Example"
    summary = "Software engineer"
 
 
@pytest.fixture
def client():
    accounts_module.init({})
    app = FastAPI()
    app.include_router(accounts_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)
 
 
def test_verify_credentials_returns_account(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.accounts.router.resolve_actor",
                   new=AsyncMock(return_value=FakePerson())):
            response = client.get("/accounts/verify_credentials")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["display_name"] == "Alice Example"
    assert data["note"] == "Software engineer"
    assert data["acct"] == "alice@example.com"
 
 
def test_verify_credentials_unknown_actor_returns_404(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.accounts.router.resolve_actor",
                   new=AsyncMock(return_value=None)):
            response = client.get("/accounts/verify_credentials")
    assert response.status_code == 404
 
 
def test_accounts_active_flag_set_after_init():
    accounts_module.init({})
    assert accounts_module.active is True

