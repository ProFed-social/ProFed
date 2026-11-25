# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import pytest
from profed.core.frozen import FrozenDict, FrozenList, frozen


DICT_METHODS = {"__class__", "__class_getitem__", "__contains__", "__delattr__", "__delitem__",
                "__dir__", "__eq__", "__format__", "__ge__", "__getattribute__", "__getitem__",
                "__getstate__", "__gt__", "__init__", "__init_subclass__", "__ior__", "__iter__",
                "__le__", "__len__", "__lt__", "__ne__", "__new__", "__or__", "__reduce__",
                "__reduce_ex__", "__repr__", "__reversed__", "__ror__", "__setattr__",
                "__setitem__", "__sizeof__", "__str__", "__subclasshook__", "clear", "copy",
                "fromkeys", "get", "items", "keys", "pop", "popitem", "setdefault", "update",
                "values"}

LIST_METHODS = {"__add__", "__class__", "__class_getitem__", "__contains__", "__delattr__",
                "__delitem__", "__dir__", "__eq__", "__format__", "__ge__", "__getattribute__",
                "__getitem__", "__getstate__", "__gt__", "__iadd__", "__imul__", "__init__",
                "__init_subclass__", "__iter__", "__le__", "__len__", "__lt__", "__mul__",
                "__ne__", "__new__", "__reduce__", "__reduce_ex__", "__repr__", "__reversed__",
                "__rmul__", "__setattr__", "__setitem__", "__sizeof__", "__str__",
                "__subclasshook__", "append", "clear", "copy", "count", "extend", "index",
                "insert", "pop", "remove", "reverse", "sort"}

MAPPING_MUTATIONS = {"__setitem__": lambda f: f.__setitem__("x", 1),
                     "__delitem__": lambda f: f.__delitem__("a"),
                     "__ior__": lambda f: f.__ior__({"x": 1}),
                     "clear": lambda f: f.clear(),
                     "pop": lambda f: f.pop("a"),
                     "popitem": lambda f: f.popitem(),
                     "setdefault": lambda f: f.setdefault("x", 1),
                     "update": lambda f: f.update({"x": 1})}

SEQUENCE_MUTATIONS = {"__setitem__": lambda f: f.__setitem__(0, 9),
                      "__delitem__": lambda f: f.__delitem__(0),
                      "__iadd__": lambda f: f.__iadd__([9]),
                      "__imul__": lambda f: f.__imul__(2),
                      "append": lambda f: f.append(9),
                      "clear": lambda f: f.clear(),
                      "extend": lambda f: f.extend([9]),
                      "insert": lambda f: f.insert(0, 9),
                      "pop": lambda f: f.pop(),
                      "remove": lambda f: f.remove(1),
                      "reverse": lambda f: f.reverse(),
                      "sort": lambda f: f.sort()}

PAYLOAD = {"id": "https://remote.example/activity/1",
           "object": {"type": "Note",
                      "attachment": [{"type": "Link", "href": "https://example.org/a"}],
                      "tag": []},
           "to": ["https://www.w3.org/ns/activitystreams#Public"],
           "count": 3,
           "summary": None}


def _callables(kind):
    return {name for name in dir(kind) if callable(getattr(kind, name))}


def test_the_methods_of_dict_are_all_accounted_for():
    assert _callables(dict) == DICT_METHODS


def test_the_methods_of_list_are_all_accounted_for():
    assert _callables(list) == LIST_METHODS


def test_every_mutating_method_of_dict_is_covered():
    assert set(MAPPING_MUTATIONS) < DICT_METHODS


def test_every_mutating_method_of_list_is_covered():
    assert set(SEQUENCE_MUTATIONS) < LIST_METHODS


@pytest.mark.parametrize("name", sorted(MAPPING_MUTATIONS))
def test_a_frozen_mapping_rejects(name):
    mapping = FrozenDict({"a": 1})

    with pytest.raises(TypeError):
        MAPPING_MUTATIONS[name](mapping)

    assert dict(mapping) == {"a": 1}


@pytest.mark.parametrize("name", sorted(SEQUENCE_MUTATIONS))
def test_a_frozen_sequence_rejects(name):
    sequence = FrozenList([1, 2])

    with pytest.raises(TypeError):
        SEQUENCE_MUTATIONS[name](sequence)

    assert list(sequence) == [1, 2]


def test_a_frozen_mapping_is_still_a_dict():
    assert isinstance(FrozenDict({"a": 1}), dict)


def test_a_frozen_sequence_is_still_a_list():
    assert isinstance(FrozenList([1]), list)


def test_freezing_reaches_nested_mappings_and_sequences():
    payload = frozen(PAYLOAD)

    assert isinstance(payload["object"], FrozenDict)
    assert isinstance(payload["object"]["attachment"], FrozenList)
    assert isinstance(payload["object"]["attachment"][0], FrozenDict)
    assert isinstance(payload["to"], FrozenList)


def test_a_nested_mapping_rejects_assignment():
    payload = frozen(PAYLOAD)

    with pytest.raises(TypeError):
        payload["object"]["attachment"][0]["href"] = "https://evil.example/"


def test_freezing_keeps_scalars_as_they_are():
    payload = frozen(PAYLOAD)

    assert payload["count"] == 3
    assert payload["summary"] is None
    assert payload["id"] == "https://remote.example/activity/1"


def test_a_frozen_payload_reads_like_the_original():
    payload = frozen(PAYLOAD)

    assert payload == PAYLOAD
    assert sorted(payload.keys()) == sorted(PAYLOAD.keys())
    assert payload.get("missing") is None
    assert len(payload["object"]["attachment"]) == 1
    assert [entry["type"] for entry in payload["object"]["attachment"]] == ["Link"]
    assert payload["to"][0].endswith("#Public")


def test_a_frozen_payload_serialises_as_json():
    assert json.loads(json.dumps(frozen(PAYLOAD))) == PAYLOAD


def test_an_empty_sequence_stays_a_sequence():
    assert isinstance(frozen(PAYLOAD)["object"]["tag"], FrozenList)


def test_freezing_something_already_frozen_changes_nothing():
    once = frozen(PAYLOAD)

    assert frozen(once) is once

