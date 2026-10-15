# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import io

import pytest
from PIL import Image
from unittest.mock import AsyncMock, patch

from profed.components.preview_activities.config import cfg
from profed.components.preview_activities import storage as preview_storage
from profed.components.preview_activities import worker
from profed.components.preview_activities.worker import make_step
from profed.core import media_storage


SENDER = "https://example.com/actors/alice"
NOTE = f"{SENDER}/notes/1"
LOCAL = "https://example.com/media/m1"
REMOTE = "https://remote.example/media/r1"


def _image(width=1280, height=720):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(buf, format="JPEG")

    return buf.getvalue()


class _Rows:
    def __init__(self, rows, files):
        self.rows = rows
        self.files = files

    async def known(self, urls):
        return [{**row, "variants": [variant
                                     for variant in ("preview", "icon")
                                     if f"{row['file_id']}_{variant}" in self.files]}
                for row in self.rows
                if row["url"] in urls]


def _row(file_id="m1", url=LOCAL, content_type="image/jpeg", variants=(), width=1280, height=720):
    return {"file_id": file_id,
            "url": url,
            "content_type": content_type,
            "width": width,
            "height": height,
            "variants": list(variants)}


def _activity(*urls):
    return {"actor": SENDER,
            "object": {"id": NOTE,
                       "type": "Note",
                       "attachment": [{"type": "Image", "mediaType": "image/jpeg", "url": url,
                                       "preview": {"type": "Image", "url": f"{url}_preview"},
                                       "icon": {"type": "Image", "url": f"{url}_icon"}}
                                      for url in urls]}}


def _item(activity, sequence_id=7):
    return ("Create", f"{SENDER}#create/1", {"username": "alice", "activity": activity}, sequence_id)


async def _drive(step, queue, rounds=8):
    outcomes = []
    for _ in range(rounds):
        outcomes.append(await step(NOTE, queue))
        if outcomes[-1] is None:
            break

    return outcomes


@pytest.fixture
def telling(fake_bus, fake_media_storage, api_config):
    with patch.object(worker, "jittered_sleep", AsyncMock()), \
         patch.dict(cfg, {"preview_delay": 0.0, "preview_dimension": 40}):
        yield fake_bus


def _storing(rows, files=None):
    return patch.object(preview_storage, "_instance", _Rows(rows, files if files is not None else {}))


def _queue(item):
    queue = asyncio.Queue()
    queue.put_nowait(item)

    return queue


async def test_a_post_without_attachments_goes_straight_out(telling):
    with _storing([]):
        await _drive(make_step(), _queue(_item({"actor": SENDER, "object": {"id": NOTE, "type": "Note"}})))

    assert len(telling.topic("deliverable_activities").published) == 1


async def test_a_post_whose_previews_exist_goes_straight_out(telling, fake_media_storage):
    with _storing([_row()], fake_media_storage._files | {"m1_preview": (), "m1_icon": ()}):
        outcomes = await _drive(make_step(), _queue(_item(_activity(LOCAL))))

    assert outcomes[-1] is None
    assert len(telling.topic("deliverable_activities").published) == 1


async def test_a_missing_preview_is_produced_before_the_post_goes_out(telling, fake_media_storage):
    fake_media_storage._files["m1"] = (_image(), "image/jpeg")

    with _storing([_row()], fake_media_storage._files):
        await _drive(make_step(), _queue(_item(_activity(LOCAL))))

    assert await fake_media_storage.retrieve("m1_preview")
    assert await fake_media_storage.retrieve("m1_icon")
    assert len(telling.topic("deliverable_activities").published) == 1


async def test_the_icon_is_square_and_the_preview_keeps_the_shape(telling, fake_media_storage):
    fake_media_storage._files["m1"] = (_image(1280, 720), "image/jpeg")

    with _storing([_row()], fake_media_storage._files):
        await _drive(make_step(), _queue(_item(_activity(LOCAL))))

    assert Image.open(io.BytesIO(await fake_media_storage.retrieve("m1_icon"))).size == (40, 40)
    assert Image.open(io.BytesIO(await fake_media_storage.retrieve("m1_preview"))).size == (40, 22)


async def test_the_post_waits_while_the_media_is_not_in_the_projection_yet(telling):
    with _storing([]):
        outcomes = await _drive(make_step(), _queue(_item(_activity(LOCAL))))

    assert outcomes == [None]
    assert telling.topic("deliverable_activities").published == []


async def test_a_remote_attachment_is_not_waited_for(telling):
    with _storing([]):
        await _drive(make_step(), _queue(_item(_activity(REMOTE))))

    assert len(telling.topic("deliverable_activities").published) == 1


async def test_a_preview_that_cannot_be_made_is_dropped_from_the_attachment(telling, fake_media_storage):
    fake_media_storage._files["m1"] = (b"not an image at all", "image/jpeg")

    with _storing([_row()], fake_media_storage._files):
        await _drive(make_step(), _queue(_item(_activity(LOCAL))))

    published = telling.topic("deliverable_activities").published
    attachment = published[0]["payload"]["activity"]["object"]["attachment"][0]

    assert len(published) == 1
    assert "preview" not in attachment
    assert "icon" not in attachment
    assert attachment["url"] == LOCAL


async def test_the_same_activity_is_forwarded_only_once(telling):
    with _storing([]):
        await _drive(make_step(), _queue(_item(_activity(REMOTE), sequence_id=11)))
        await _drive(make_step(), _queue(_item(_activity(REMOTE), sequence_id=11)))

    assert len(telling.topic("deliverable_activities").published) == 1

