# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core import memory


class WithTrim:
    def __init__(self, calls):
        self._calls = calls

    def malloc_trim(self, padding):
        self._calls.append(padding)

        return 1


class WithoutTrim:
    pass


def test_release_reports_whether_it_handed_anything_back():
    assert isinstance(memory.release(), bool)


def test_release_asks_for_no_padding(monkeypatch):
    calls = []
    monkeypatch.setattr(memory.ctypes, "CDLL", lambda name: WithTrim(calls))

    assert memory._make_release()() is True
    assert calls == [0]


def test_a_library_without_malloc_trim_hands_nothing_back(monkeypatch):
    monkeypatch.setattr(memory.ctypes, "CDLL", lambda name: WithoutTrim())

    assert memory._make_release()() is False


def test_a_library_that_will_not_load_hands_nothing_back(monkeypatch):
    def refuse(name):
        raise OSError("no such library")

    monkeypatch.setattr(memory.ctypes, "CDLL", refuse)

    assert memory._make_release()() is False

