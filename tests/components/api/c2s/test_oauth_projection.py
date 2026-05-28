# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import time
import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.oauth import projection


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
APP_PAYLOAD = {"client_secret": "secret",
               "client_name":   "TestApp",
               "redirect_uris": "https://app.example.com/callback",
               "scopes":        "read write"}
EXPECTED_APP = {"client_id": "abc123", **APP_PAYLOAD}


@pytest.mark.asyncio
async def test_app_created_added_to_projection(fake_bus):
    fake_bus.topic("oauth_apps").messages = [
            (1, "created", "abc123", TS, APP_PAYLOAD)]

    await projection.apps_rebuild()

    assert projection.get_app("abc123") == EXPECTED_APP


@pytest.mark.asyncio
async def test_unknown_app_returns_none(fake_bus):
    fake_bus.topic("oauth_apps").messages = []

    await projection.apps_rebuild()

    assert projection.get_app("unknown") is None


@pytest.mark.asyncio
async def test_code_issued_added_to_projection(fake_bus):
    payload = {"client_id":  "abc123",
               "username":   "alice",
               "id_token":   "tok",
               "expires_at": time.time() + 600}
    fake_bus.topic("oauth_codes").messages = [
            (1, "issued", "mycode", TS, payload)]

    await projection.codes_rebuild()

    assert projection.get_code("mycode") == {"code": "mycode", **payload}


@pytest.mark.asyncio
async def test_expired_code_returns_none(fake_bus):
    payload = {"client_id":  "abc123",
               "username":   "alice",
               "id_token":   "tok",
               "expires_at": time.time() - 1}
    fake_bus.topic("oauth_codes").messages = [
            (1, "issued", "mycode", TS, payload)]

    await projection.codes_rebuild()

    assert projection.get_code("mycode") is None


@pytest.mark.asyncio
async def test_consumed_code_removed_from_projection(fake_bus):
    payload = {"client_id":  "abc123",
               "username":   "alice",
               "id_token":   "tok",
               "expires_at": time.time() + 600}
    fake_bus.topic("oauth_codes").messages = [
            (1, "issued",   "mycode", TS, payload),
            (2, "consumed", "mycode", TS, {})]

    await projection.codes_rebuild()

    assert projection.get_code("mycode") is None

