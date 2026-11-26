# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import patch

from profed.components.preview_activities import translator


SENDER = "https://example.com/actors/alice"
NOTE = f"{SENDER}/notes/1"
CREATE = f"{SENDER}#create/1"


class Collecting:
    def __init__(self):
        self.submitted = []

    def submit(self, key, item):
        self.submitted.append((key, item))


def _payload(object_id=NOTE):
    return {"username": "alice", "activity": {"actor": SENDER, "object": {"id": object_id, "type": "Note"}}}


async def test_an_activity_reaches_the_workers():
    collecting = Collecting()

    with patch.object(translator, "_workers", collecting):
        await translator._submit("Create", CREATE, _payload(), 7)

    assert collecting.submitted == [(NOTE, ("Create", CREATE, _payload(), 7))]


async def test_the_object_is_the_key_not_the_activity():
    collecting = Collecting()

    with patch.object(translator, "_workers", collecting):
        await translator._submit("Create", CREATE, _payload("https://example.com/notes/other"), 7)

    assert collecting.submitted[0][0] == "https://example.com/notes/other"


async def test_an_activity_whose_object_is_a_bare_url_keys_on_its_own_id():
    collecting = Collecting()

    with patch.object(translator, "_workers", collecting):
        await translator._submit("Delete", CREATE, {"username": "alice", "activity": {"object": NOTE}}, 7)

    assert collecting.submitted[0][0] == CREATE

