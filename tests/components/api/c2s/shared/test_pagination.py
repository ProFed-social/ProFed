# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from types import SimpleNamespace
from profed.components.api.c2s.shared.pagination import cursor_in, only, the_id, unchanged


def test_the_id_reads_the_attribute_of_a_model():
    assert the_id(SimpleNamespace(id="424242")) == "424242"


def test_a_cursor_in_a_field_comes_back_as_text():
    assert cursor_in("marked_at")({"marked_at": 500}) == "500"


def test_two_cursors_read_their_own_field():
    row = {"marked_at": 500, "mastodon_id": 7}

    assert (cursor_in("marked_at")(row), cursor_in("mastodon_id")(row)) == ("500", "7")


def test_only_keeps_one_field_of_every_row():
    assert only("status")([{"marked_at": 5, "status": "a"}, {"marked_at": 4, "status": "b"}]) == ["a", "b"]


def test_only_of_an_empty_page_is_empty():
    assert only("status")([]) == []


def test_unchanged_hands_the_rows_back():
    rows = [{"a": 1}]

    assert unchanged(rows) is rows

