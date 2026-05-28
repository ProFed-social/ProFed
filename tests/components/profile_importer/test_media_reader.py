# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.profile_importer import media_reader


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _media(fake_bus):
    return fake_bus.topic("media")


def _uploaded(seq: int, source_url: str, file_id: str = "abc"):
    return (seq, "uploaded", file_id, TS, {"url": f"https://cdn.example.com/{file_id[:2]}/{file_id}",
                                           "content_type": "image/jpeg",
                                           "size": 1024,
                                           "uploader": "alice@example.com",
                                           "source_url": source_url})


def _deleted(seq: int, file_id: str):
    return (seq, "deleted", file_id, TS, {})


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
    _media(fake_bus).messages = [_uploaded(1, "https://example.com/photo.jpg",  "id1"),
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
                                 _deleted (2, "id1")]
    urls = frozenset(["https://example.com/photo.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert "https://example.com/photo.jpg" not in state


@pytest.mark.asyncio
async def test_reading_media_state_snapshot_is_applied(fake_bus):
    _media(fake_bus).snapshots = [(5, [{"file_id":    "snap",
                                        "url":        "https://cdn.example.com/ab/snap",
                                        "source_url": "https://example.com/photo.jpg"}])]
    urls = frozenset(["https://example.com/photo.jpg"])

    async with media_reader.reading_media_state(urls) as (state, caught_up):
        await caught_up.wait()

    assert state["https://example.com/photo.jpg"]["file_id"] == "snap"

