# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.shared.media import projection
from profed.components.api.c2s.shared.media import storage as storage_module


UPLOADED = {"url": "https://cdn.example.com/ab/abc123",
            "content_type": "image/jpeg",
            "size": 4711,
            "uploader": "alice@example.com",
            "description": "Ein Diagramm",
            "metadata": {"kind": "image", "width": 1920, "height": 1080}}


class FakeStorage:
    def __init__(self):
        self.rows = {}

    async def insert(self, file_id, **columns):
        self.rows[file_id] = columns

    async def delete(self, file_id):
        self.rows.pop(file_id, None)


@pytest.fixture
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()

    yield storage_module._instance

    storage_module._instance = backup


@pytest.mark.asyncio
async def test_an_uploaded_object_is_kept_with_its_dimensions(store):
    await projection._uploaded("abc123", UPLOADED)

    assert store.rows["abc123"]["width"] == 1920
    assert store.rows["abc123"]["height"] == 1080


@pytest.mark.asyncio
async def test_the_alt_text_reaches_the_stored_row(store):
    await projection._uploaded("abc123", UPLOADED)

    assert store.rows["abc123"]["description"] == "Ein Diagramm"


@pytest.mark.asyncio
async def test_an_object_without_an_alt_text_keeps_none(store):
    await projection._uploaded("abc123", {k: v for k, v in UPLOADED.items() if k != "description"})

    assert store.rows["abc123"]["description"] is None


@pytest.mark.asyncio
async def test_an_object_without_dimensions_keeps_none(store):
    await projection._uploaded("abc123", {k: v for k, v in UPLOADED.items() if k != "metadata"})

    assert store.rows["abc123"]["width"] is None
    assert store.rows["abc123"]["height"] is None


@pytest.mark.asyncio
async def test_a_snapshot_item_takes_the_same_route(store):
    await projection._uploaded_snapshot(dict(UPLOADED, file_id="abc123"))

    assert store.rows["abc123"]["description"] == "Ein Diagramm"


@pytest.mark.asyncio
async def test_a_deleted_object_is_gone(store):
    await projection._uploaded("abc123", UPLOADED)

    await projection._deleted("abc123", {})

    assert "abc123" not in store.rows

