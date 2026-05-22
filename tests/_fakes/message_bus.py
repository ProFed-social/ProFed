# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


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
        async def _publish(event, message_id=None):
            if message_id is not None:
                if message_id in self._topic._published_ids:
                    return
                self._topic._published_ids.add(message_id)
            seq = len(self._topic.messages) + 1
            self._topic.messages.append((seq, event))
            self._topic.published.append(event)
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

    def subscribe(self,
                  subscriber,
                  last_seen=0,
                  include_sequence_id=False,
                  include_emitted_at=False,
                  caught_up=None):
        async def generator():
            for seq, event in self.messages:
                if seq > last_seen:
                    self.last_seen = seq
                    next_result = (((seq,)  if include_sequence_id else ()) +
                                   ((None,) if include_emitted_at  else ()) +
                                   (event,))
                    yield next_result if len(next_result) > 1 else next_result[0]
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

