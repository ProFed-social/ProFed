# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone


class FakeLastSnapshot:
    def __init__(self, event_id=0, items=None):
        self._event_id = event_id
        self._items    = items or []

    async def __call__(self):
        return self._event_id, self._items


class FakePublishContext:
    def __init__(self, topic):
        self._topic = topic

    async def __aenter__(self):
        async def _publish(event_type,
                           object_id,
                           payload=None,
                           message_id=None):
            if message_id is not None:
                if message_id in self._topic._published_ids:
                    return
                self._topic._published_ids.add(message_id)
            seq     = len(self._topic.messages) + 1
            payload = payload if payload is not None else {}
            self._topic.messages.append((seq,
                                         event_type,
                                         object_id,
                                         datetime.now(timezone.utc),
                                         payload))
            self._topic.published.append({"event_type": event_type,
                                          "object_id":  object_id,
                                          "payload":    payload})
        return _publish

    async def __aexit__(self, *_):
        pass


class FakeTopic:
    def __init__(self):
        self.messages  = []   # [(seq, event_type, object_id, emitted_at, payload), ...]
        self.published = []   # [{"event_type", "object_id", "payload"}, ...]
        self.snapshots = []   # [(last_event_id, items), ...]
        self.last_seen = 0
        self._published_ids = set()

    async def last_snapshot(self):
        return self.snapshots[-1] if self.snapshots else (0, [])

    async def last_snapshot_id(self):
        return self.snapshots[-1][0] if self.snapshots else 0

    def subscribe(self, subscriber, last_seen=0, caught_up=None):
        async def generator():
            for msg in self.messages:
                if msg[0] > last_seen:
                    self.last_seen = msg[0]
                    yield msg
            if caught_up is not None:
                caught_up.set()
        return generator()

    def publish(self):
        return FakePublishContext(self)


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]

