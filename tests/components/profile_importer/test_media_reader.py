# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from profed.core import message_bus
from profed.components.profile_importer import media_reader


class FakeLastSnapshot:
    def __init__(self, event_id=0, items=None):
        self._event_id = event_id
        self._items    = items or []

    async def __call__(self):
        return self._event_id, self._items


class FakeTopic:
    def __init__(self):
        self.messages      = []
        self._last_snapshot = FakeLastSnapshot()

    def last_snapshot(self):
        return self._last_snapshot()

    def subscribe(self,
                  subscriber,
                  last_seen=0,
                  include_sequence_id=False,
                  include_emitted_at=False,
                  caught_up=None):
        async def generator():
            for seq, event in self.messages:
                if seq > last_seen:
                    next_result = (((seq,)  if include_sequence_id else ()) +
                                   ((None,) if include_emitted_at  else ()) +
                                   (event,))
                    yield next_result if len(next_result) > 1 else next_result[0]
            if caught_up is not None:
                caught_up.set()
            await asyncio.sleep(10_000)
        return generator()


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]


@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()

    yield message_bus._instance

    message_bus._instance = backup


def _media(fake_bus):
    return fake_bus.topic("media")


def _uploaded(seq, source_url, file_id="abc", url="https://cdn.example.com/ab/abc"):
    return (seq, {"type":    "uploaded",
                  "payload": {"file_id":      file_id,
                              "url":          url,
                              "content_type": "image/jpeg",
                              "size":         1024,
                              "uploader":     "alice@example.com",
                              "source_url":   source_url}})


@pytest.mark.asyncio
async def test_reading_media_state_returns_empty_when_no_matching_events(fake_bus):
    _media(fake_bus).messages = [_uploaded(1, "https://example.com/other.jpg")]
    urls = frozenset(["https://example.com/photo.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert state == {}


@pytest.mark.asyncio
async def test_reading_media_state_returns_matching_entry(fake_bus):
    _media(fake_bus).messages = [_uploaded(1, "https://example.com/photo.jpg")]
    urls = frozenset(["https://example.com/photo.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert "https://example.com/photo.jpg" in state
    assert state["https://example.com/photo.jpg"]["file_id"] == "abc"


@pytest.mark.asyncio
async def test_reading_media_state_handles_multiple_urls_in_one_pass(fake_bus):
    _media(fake_bus).messages = [_uploaded(1, "https://example.com/photo.jpg", "id1"),
                                  _uploaded(2, "https://example.com/banner.jpg", "id2")]
    urls = frozenset(["https://example.com/photo.jpg",
                      "https://example.com/banner.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert state["https://example.com/photo.jpg"]["file_id"]  == "id1"
    assert state["https://example.com/banner.jpg"]["file_id"] == "id2"


@pytest.mark.asyncio
async def test_reading_media_state_deleted_event_removes_entry(fake_bus):
    _media(fake_bus).messages = [_uploaded(1, "https://example.com/photo.jpg", "id1"),
                                  (2, {"type":    "deleted",
                                       "payload": {"file_id": "id1"}})]
    urls = frozenset(["https://example.com/photo.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert "https://example.com/photo.jpg" not in state


@pytest.mark.asyncio
async def test_reading_media_state_snapshot_is_applied(fake_bus):
    _media(fake_bus)._last_snapshot = FakeLastSnapshot(
        event_id=5,
        items=[{"file_id":    "snap",
                "url":        "https://cdn.example.com/ab/snap",
                "source_url": "https://example.com/photo.jpg"}])
    urls = frozenset(["https://example.com/photo.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert state["https://example.com/photo.jpg"]["file_id"] == "snap"

