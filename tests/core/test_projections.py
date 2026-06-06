# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence import projections


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

