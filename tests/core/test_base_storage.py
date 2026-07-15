# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from profed.core.persistence.base_storage import BaseStorage, wait_for_rebuild


class _FakeConn:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    async def fetchrow(self, sql, *args):
        return self._row

    async def fetch(self, sql, *args):
        return self._rows


class _Acquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _Acquire(self._conn)


def _storage(row=None, rows=None):
    s = BaseStorage(_FakePool(_FakeConn(row, rows)), None)
    s._is_rebuilt = asyncio.Event()
    return s


class _Dummy(BaseStorage):
    def __init__(self):
        self._is_rebuilt = asyncio.Event()
        self.calls = 0

    @wait_for_rebuild
    async def read(self):
        self.calls += 1
        return "data"


async def test_read_blocks_until_rebuild_finished():
    d = _Dummy()

    task = asyncio.create_task(d.read())

    await asyncio.sleep(0)
    assert not task.done()
    d.rebuild_finished()
    assert await task == "data"


async def test_barrier_is_nulled_after_first_read():
    d = _Dummy()

    d.rebuild_finished()

    await d.read()
    assert d._is_rebuilt is None
    await d.read()
    assert d.calls == 2


async def test_rebuild_finished_is_safe_after_nulling():
    d = _Dummy()

    d.rebuild_finished()

    await d.read()
    d.rebuild_finished()


async def test_fetch_one_is_gated():
    s = _storage(row={"x": 1})

    task = asyncio.create_task(s.fetch_one("SELECT 1"))

    await asyncio.sleep(0)
    assert not task.done()
    s.rebuild_finished()
    assert await task == {"x": 1}


async def test_fetch_all_is_gated():
    s = _storage(rows=[{"x": 1}, {"x": 2}])

    task = asyncio.create_task(s.fetch_all("SELECT 1"))

    await asyncio.sleep(0)
    assert not task.done()
    s.rebuild_finished()
    assert await task == [{"x": 1}, {"x": 2}]


async def test_fetch_returns_immediately_once_rebuilt():
    s = _storage(row={"x": 1})

    s.rebuild_finished()

    assert await s.fetch_one("SELECT 1") == {"x": 1}
    assert s._is_rebuilt is None

