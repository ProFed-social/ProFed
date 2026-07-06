# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence import projections
from profed.sanitize import sanitize_as_object


class _FakeTopic:
    async def last_snapshot(self):
        return 0, []

    def subscribe(self, subscriber, last_seen=0, caught_up=None):
        async def _gen():
            if caught_up is not None:
                caught_up.set()
            if False:
                yield None
        return _gen()


class _FakeBus:
    def topic(self, name):
        return _FakeTopic()


_TOPIC = {"name": "t",
          "validate": lambda et, p: p,
          "snapshot_validate": lambda i: i}


async def _noop():
    pass


async def test_rebuild_calls_rebuild_finished(monkeypatch):
    monkeypatch.setattr(projections, "message_bus", lambda: _FakeBus())
    called = []

    async def _spy():
        called.append(True)

    _, rebuild, _ = projections.build_projection(topic=_TOPIC,
                                                 subscriber="s",
                                                 init=_noop,
                                                 on_snapshot_item=_noop,
                                                 on_message_type={},
                                                 rebuild_finished=_spy)
    await rebuild()
    assert called == [True]


async def test_rebuild_finished_defaults_to_noop(monkeypatch):
    monkeypatch.setattr(projections, "message_bus", lambda: _FakeBus())

    _, rebuild, _ = projections.build_projection(topic=_TOPIC,
                                                 subscriber="s",
                                                 init=_noop,
                                                 on_snapshot_item=_noop,
                                                 on_message_type={})
    await rebuild()


class _HealTopic:
    def __init__(self, messages):
        self.messages = messages
        self.published = []
        self._ids = set()

    async def last_snapshot(self):
        return 0, []

    def subscribe(self, subscriber, last_seen=0, caught_up=None):
        async def _gen():
            for msg in self.messages:
                yield msg

        return _gen()

    def publish(self):
        return _HealPublish(self)


class _HealPublish:
    def __init__(self, topic):
        self._topic = topic

    async def __aenter__(self):
        async def _publish(event_type, object_id, payload=None, message_id=None):
            if message_id in self._topic._ids:
                return None

            self._topic._ids.add(message_id)
            self._topic.published.append({"event_type": event_type,
                                          "object_id":  object_id,
                                          "payload":    payload})

            return len(self._topic.published)
        return _publish

    async def __aexit__(self, *_):
        pass


class _HealBus:
    def __init__(self, topic):
        self._topic = topic

    def topic(self, name):
        return self._topic


_HEAL_TOPIC = {"name":                "t",
               "validate":            lambda et, p: p,
               "snapshot_validate":   lambda i: i,
               "sanitize":            sanitize_as_object,
               "correction_verb_map": {"Create": "Update", "created": "updated"}}


def _heal_projection(received, subscriber="s"):
    async def _handler(object_id, payload):
        received.append(payload)
    handle, _, _ = projections.build_projection(topic=_HEAL_TOPIC,
                                                subscriber=subscriber,
                                                init=_noop,
                                                on_snapshot_item=_noop,
                                                on_message_type={"created": _handler,
                                                                 "Create": _handler})
    return handle


async def test_dispatch_sanitises_and_publishes_correction(fake_bus):
    fake_bus.topic("t").messages = [(1, "created", "alice", None, {"summary": "<p>ok</p><script>s</script>"})]
    received = []

    await _heal_projection(received)()

    assert received == [{"summary": "<p>ok</p>"}]
    assert fake_bus.topic("t").published == [{"event_type": "updated",
                                              "object_id": "alice",
                                              "payload": {"summary": "<p>ok</p>"}}]


async def test_correction_maps_create_to_update(fake_bus):
    fake_bus.topic("t").messages = [(1, "Create", "n1", None, {"content": "<p>x</p><script>s</script>"})]

    await _heal_projection([])()

    assert fake_bus.topic("t").published[0]["event_type"] == "Update"


async def test_clean_payload_publishes_no_correction(fake_bus):
    fake_bus.topic("t").messages = [(1, "created", "alice", None, {"summary": "<p>clean</p>"})]

    await _heal_projection([])()

    assert fake_bus.topic("t").published == []


async def test_correction_deduped_across_instances_logs_once(fake_bus, caplog):
    fake_bus.topic("t").messages = [(1, "created", "alice", None, {"summary": "<p>ok</p><script>s</script>"})]

    with caplog.at_level("WARNING"):
        await _heal_projection([], subscriber="s1")()
        await _heal_projection([], subscriber="s2")()

    corrections = [p for p in fake_bus.topic("t").published if p["event_type"] == "updated"]
    assert len(corrections) == 1
    assert caplog.text.count("second line healed") == 1
