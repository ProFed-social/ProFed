# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import os
import asyncio
from typing import Dict
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from profed.core.config import config, raw
from profed.components.activity_delivery import handler, delivery
from profed.components.activity_delivery import storage as storage_module


TS        = datetime(2026, 1, 1, tzinfo=timezone.utc)
INBOX_URL = "https://remote.example/inbox/bob"
ACTIVITY  = {"id":    "https://example.com/act/1",
             "type":  "Create",
             "actor": "https://example.com/actors/alice"}


class FakeStorage:
    async def get_followers(self, following):
        return {"bob@remote.example"}

    async def get_delivery_status(self, activity_id, recipient):
        return None

    async def upsert_delivery(self, payload):
        pass

    async def get_user_key(self, username):
        return None


class Cfg:
    def __init__(self, cfg: Dict[str, Dict[str, str]]):
        raw.paths = []
        raw.argv  = [""] + [f"--{section}.{parameter}={value}"
                            for section, s in cfg.items()
                            for parameter, value in s.items()]
        os.environ = {k: v for k, v in os.environ.items()
                      if not k.startswith("PROFED_")}

    def __enter__(self):
        config.reset()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val


@pytest.fixture
def fake_storage():
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = None


def _mock_post_response(status=202):
    r = MagicMock()
    r.status_code = status
    r.headers = {}

    return r


def _activity_message(seq, activity, username="alice"):
    activity_id = activity["id"]
    event_type  = activity["type"]
    inner       = {k: v for k, v in activity.items() if k not in ("id", "type")}
    return (seq, event_type, activity_id, TS, {"username": username,
                                               "activity": inner})


@pytest.mark.asyncio
async def test_handle_activities_creates_delivery_task(fake_bus, fake_storage):
    fake_bus.topic("activities").messages = [_activity_message(1, ACTIVITY)]

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch.object(handler, "deliver", new=AsyncMock()) as mock_deliver, \
             patch("profed.components.activity_delivery.handler.asyncio.create_task",
                   side_effect=lambda coro, **kw: asyncio.ensure_future(coro)):
            await handler.handle_activities({"domain": "example.com"})

            await asyncio.sleep(0)
            mock_deliver.assert_awaited_once()
            call_args = mock_deliver.call_args[0]
            assert call_args[1] == "https://example.com/act/1"
            assert call_args[3] == "bob@remote.example"


@pytest.mark.asyncio
async def test_handle_activities_invalid_payload_is_ignored(fake_bus, fake_storage):
    fake_bus.topic("activities").messages = [
            (1, "Create", "https://example.com/act/1", TS,
             {"activity": {"actor": "https://example.com/actors/alice"}})]

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch.object(handler, "deliver", new=AsyncMock()) as mock_deliver, \
             patch("profed.components.activity_delivery.handler.asyncio.create_task",
                   side_effect=lambda coro, **kw: asyncio.ensure_future(coro)):
            await handler.handle_activities({"domain": "example.com"})

            await asyncio.sleep(0)
            mock_deliver.assert_not_awaited()


@pytest.mark.asyncio
async def test_deliver_skips_already_successful(fake_bus, fake_storage):
    storage_module._instance.get_delivery_status = AsyncMock(
        return_value={"success":          True,
                      "attempt":          1,
                      "retry_after":      None,
                      "first_attempt_at": datetime.now(timezone.utc)})

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        await delivery.deliver({},
                               "https://example.com/act/1",
                               ACTIVITY,
                               "bob@remote.example")

    assert fake_bus.topic("deliveries").published == []


@pytest.mark.asyncio
async def test_deliver_publishes_delivery_succeeded(fake_bus, fake_storage):
    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.activity_delivery.delivery._fetch_inbox_url",
                   AsyncMock(return_value=INBOX_URL)), \
             patch("profed.components.activity_delivery.delivery.httpx.AsyncClient") as mock_post:
            mock_post.return_value.__aenter__.return_value.post = \
                    AsyncMock(return_value=_mock_post_response(status=202))
            await delivery.deliver({"initial_retry": 0},
                                   "https://example.com/act/1",
                                   ACTIVITY,
                                   "bob@remote.example")

            published = fake_bus.topic("deliveries").published
            assert len(published) == 1
            assert published[0]["event_type"] == "delivery_succeeded"
            assert published[0]["object_id"]  == "https://example.com/act/1|bob@remote.example"


@pytest.mark.asyncio
async def test_deliver_publishes_delivery_failed(fake_bus, fake_storage):
    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.activity_delivery.delivery._fetch_inbox_url",
                   AsyncMock(return_value=INBOX_URL)), \
             patch("profed.components.activity_delivery.delivery.httpx.AsyncClient") as mock_post:
            mock_post.return_value.__aenter__.return_value.post = \
                    AsyncMock(return_value=_mock_post_response(status=500))
            await delivery.deliver({"initial_retry": 0},
                                   "https://example.com/act/1",
                                   ACTIVITY,
                                   "bob@remote.example")

            published = fake_bus.topic("deliveries").published
            assert len(published) == 1
            assert published[0]["event_type"]              == "delivery_failed"
            assert published[0]["payload"]["status_code"]  == 500


@pytest.mark.asyncio
async def test_deliver_sends_signed_request_when_key_available(fake_bus, fake_storage):
    from profed.http.signatures import generate_key_pair
    public_pem, private_pem      = generate_key_pair()
    fake_storage.get_user_key    = AsyncMock(return_value=(public_pem, private_pem))

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.activity_delivery.delivery._fetch_inbox_url",
                   AsyncMock(return_value=INBOX_URL)), \
             patch("profed.components.activity_delivery.delivery.httpx.AsyncClient") as mock_post:
            mock_post.return_value.__aenter__.return_value.post = \
                    AsyncMock(return_value=_mock_post_response(status=202))
            await delivery.deliver({"initial_retry": 0},
                                   "https://example.com/act/1",
                                   ACTIVITY,
                                   "bob@remote.example")

            call_kwargs = mock_post.return_value.__aenter__.return_value.post.call_args
            headers     = call_kwargs.kwargs["headers"]
            assert "Signature" in headers
            assert "Digest"    in headers
            assert "Date"      in headers

