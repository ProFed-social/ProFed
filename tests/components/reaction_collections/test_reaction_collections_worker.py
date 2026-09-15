# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from profed.components.reaction_collections import storage as storage_module
from profed.components.reaction_collections import translator, worker
from profed.topics.reactions_resolution_topic import claim_id


NOTE = "https://remote.example/notes/7"

REACTIONS = f"{NOTE}/emojiReactions"


def _like(n, **rest):
    return {"id": f"https://r.example/users/bob#react/{n}",
            "type": "Like",
            "actor": "https://r.example/users/bob",
            "object": NOTE,
            "content": "🎉",
            **rest}


class FakeStorage:
    def __init__(self, due=None):
        self.rows = due if due is not None else []
        self.asked = []

    async def due(self, object_urls, now, lease):
        self.asked.append({"urls": object_urls, "lease": lease})
        return self.rows


@pytest.fixture
def store():
    backup = storage_module._instance

    def _use(due=None):
        storage_module._instance = FakeStorage(due)
        return storage_module._instance

    yield _use
    storage_module._instance = backup


def _reported(fake_bus):
    return [(message["event_type"], message["payload"])
            for message in fake_bus.topic("reactions_resolution").published]


@pytest.fixture(autouse=True)
def fresh():
    worker.configure({"max_pages": 500, "refresh_after": timedelta(hours=1)})
    worker._queue = asyncio.Queue(maxsize=worker.QUEUE_SIZE)
    yield


def _documents(pages):
    async def _get(url):
        return pages[url]

    return patch.object(worker, "_document", AsyncMock(side_effect=_get))


def test_the_message_id_follows_the_reaction_url():
    assert worker.message_id_of("https://r/1") == worker.message_id_of("https://r/1")
    assert worker.message_id_of("https://r/1") != worker.message_id_of("https://r/2")


@pytest.mark.asyncio
async def test_the_reactions_of_a_collection_are_handed_on(fake_bus, store):
    store()
    pages = {REACTIONS: {"totalItems": 2, "orderedItems": [_like(1), _like(2)]}}

    with _documents(pages):
        await worker.refresh(NOTE, REACTIONS)

    published = fake_bus.topic("incoming_activities").published
    assert [message["object_id"] for message in published] == [_like(1)["id"], _like(2)["id"]]
    assert published[0]["payload"]["activity"]["content"] == "🎉"


@pytest.mark.asyncio
async def test_what_is_not_a_reaction_on_this_object_is_not_handed_on(fake_bus, store):
    store()
    foreign = _like(3, object="https://elsewhere.example/notes/1")
    pages = {REACTIONS: {"totalItems": 3, "orderedItems": [_like(1), foreign, _like(2, type="Announce")]}}

    with _documents(pages):
        await worker.refresh(NOTE, REACTIONS)

    assert [m["object_id"] for m in fake_bus.topic("incoming_activities").published] == [_like(1)["id"]]


@pytest.mark.asyncio
async def test_a_finished_read_is_reported_as_succeeded(fake_bus, store):
    store()

    with _documents({REACTIONS: {"totalItems": 0, "orderedItems": []}}):
        await worker.refresh(NOTE, REACTIONS)

    state, payload = _reported(fake_bus)[0]
    assert state == "succeeded"
    assert payload["attempt"] == 0
    assert payload["object_url"] == NOTE


@pytest.mark.asyncio
async def test_a_failed_read_counts_up_and_waits(fake_bus, store):
    store()

    with patch.object(worker, "_document", AsyncMock(side_effect=RuntimeError("boom"))):
        await worker.refresh(NOTE, REACTIONS, attempt=2)

    state, payload = _reported(fake_bus)[0]
    assert state == "failed"
    assert payload["attempt"] == 3


@pytest.mark.asyncio
async def test_a_later_attempt_waits_longer(fake_bus, store):
    store()
    frozen = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with patch.object(worker, "_document", AsyncMock(side_effect=RuntimeError("boom"))), \
         patch.object(worker, "_now", lambda: frozen):
        await worker.refresh(NOTE, REACTIONS, attempt=0)
        await worker.refresh(NOTE, REACTIONS, attempt=4)

    first, later = [payload["next_due_at"] for _, payload in _reported(fake_bus)]
    assert later > first


@pytest.mark.asyncio
async def test_reading_follows_the_next_page(fake_bus, store):
    store()
    second = f"{REACTIONS}?page=true&before=1"
    pages = {REACTIONS: {"totalItems": 2, "first": {"orderedItems": [_like(2)], "next": second}},
             second: {"orderedItems": [_like(1)]}}

    with _documents(pages):
        await worker.refresh(NOTE, REACTIONS)

    assert len(fake_bus.topic("incoming_activities").published) == 2


@pytest.mark.asyncio
async def test_reading_stops_when_the_announced_total_is_reached(fake_bus, store):
    store()
    never = "https://r.example/never"
    pages = {REACTIONS: {"totalItems": 1, "first": {"orderedItems": [_like(1)], "next": never}},
             never: {"orderedItems": [_like(2)]}}

    with _documents(pages) as asked:
        await worker.refresh(NOTE, REACTIONS)

    assert len(fake_bus.topic("incoming_activities").published) == 1
    assert never not in [call.args[0] for call in asked.await_args_list]


@pytest.mark.asyncio
async def test_a_full_queue_lets_the_object_try_again_later(fake_bus, store):
    store()
    for n in range(worker.QUEUE_SIZE):
        worker._queue.put_nowait((f"https://r/{n}", REACTIONS, 0))

    await worker.enqueue(NOTE, REACTIONS)

    state, payload = _reported(fake_bus)[0]
    assert state == "failed"
    assert payload["attempt"] == 1


@pytest.mark.asyncio
async def test_a_due_object_is_claimed_and_queued(fake_bus, store):
    store([{"object_url": NOTE, "collection_url": REACTIONS, "attempt": 2}])
    translator.configure({"lease": timedelta(minutes=5)})

    await translator._on_requested(NOTE, {"object_urls": [NOTE]})

    assert _reported(fake_bus)[0][0] == "attempting"
    assert worker._queue.get_nowait() == (NOTE, REACTIONS, 2)


def test_the_claim_is_the_same_for_every_instance():
    assert claim_id(NOTE, 2) == claim_id(NOTE, 2)


def test_a_later_attempt_is_a_new_claim():
    assert claim_id(NOTE, 2) != claim_id(NOTE, 3)


def test_another_object_is_another_claim():
    assert claim_id(NOTE, 2) != claim_id("https://r/8", 2)


@pytest.mark.asyncio
async def test_an_object_that_is_not_due_is_not_queued(fake_bus, store):
    store([])
    translator.configure({"lease": timedelta(minutes=5)})

    await translator._on_requested(NOTE, {"object_urls": [NOTE]})

    assert worker._queue.empty()
    assert _reported(fake_bus) == []


@pytest.mark.asyncio
async def test_the_whole_batch_is_offered_for_claiming(store):
    keeper = store([])
    translator.configure({"lease": timedelta(minutes=5)})

    await translator._on_requested(NOTE, {"object_urls": [NOTE, "https://r/8"]})

    assert keeper.asked[0]["urls"] == [NOTE, "https://r/8"]


@pytest.mark.asyncio
async def test_the_runner_takes_work_from_the_queue(fake_bus, store):
    store()
    worker._queue.put_nowait((NOTE, REACTIONS, 0))

    with _documents({REACTIONS: {"totalItems": 0, "orderedItems": []}}):
        task = asyncio.create_task(worker.run())
        await asyncio.wait_for(worker._queue.join(), timeout=5)
        task.cancel()

    assert _reported(fake_bus)[0][1]["object_url"] == NOTE

