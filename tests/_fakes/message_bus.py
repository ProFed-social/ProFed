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
                    return None
                self._topic._published_ids.add(message_id)
            seq = len(self._topic.messages) + 1
            payload = payload if payload is not None else {}
            self._topic.messages.append((seq,
                                         event_type,
                                         object_id,
                                         datetime.now(timezone.utc),
                                         payload))
            self._topic.published.append({"event_type": event_type,
                                          "object_id": object_id,
                                          "payload": payload})
            return seq
        return _publish

    async def __aexit__(self, *_):
        pass


class FakeTopic:
    def __init__(self):
        self.messages  = []
        self.published = []
        self.snapshots = []
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


class MessageIdLookupFakeTopic(FakeTopic):
    async def exists(self, message_id) -> bool:
        return message_id in self._published_ids


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

    def topic(self, name, lookup_message_ids=False):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        if lookup_message_ids and type(self._topics[name]) is FakeTopic:
            self._topics[name].__class__ = MessageIdLookupFakeTopic
        return self._topics[name]

