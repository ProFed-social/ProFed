# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.c2s.shared.statuses.hidden import HIDDEN_CONTENT, as_rows, collapse


def _row(url, parent, visible, mastodon_id=None):
    return {"url": url,
            "in_reply_to": parent,
            "visible": visible,
            "mastodon_id": mastodon_id or f"id-{url}",
            "emitted_at": "2026-10-01T12:00:00+00:00"}


def test_a_tree_without_anything_hidden_stays_as_it_is():
    rows = [_row("root", None, True), _row("a", "root", True)]

    shown, placeholders = collapse(rows)

    assert [row["url"] for row in shown] == ["root", "a"]
    assert placeholders == []


def test_a_run_of_hidden_posts_becomes_one_placeholder():
    rows = [_row("root", None, True),
            _row("a", "root", False),
            _row("b", "a", False),
            _row("c", "b", True)]

    shown, placeholders = collapse(rows)

    assert [row["url"] for row in shown] == ["root", "c"]
    assert [p["url"] for p in placeholders] == ["a"]


def test_the_placeholder_takes_the_id_of_the_topmost_hidden_post():
    rows = [_row("root", None, True),
            _row("a", "root", False, "4711"),
            _row("b", "a", False, "4712"),
            _row("c", "b", True)]

    _, placeholders = collapse(rows)

    assert placeholders[0]["mastodon_id"] == "4711"


def test_the_placeholder_hangs_below_the_nearest_visible_ancestor():
    rows = [_row("root", None, True),
            _row("a", "root", False),
            _row("b", "a", False),
            _row("c", "b", True)]

    _, placeholders = collapse(rows)

    assert placeholders[0]["in_reply_to"] == "root"


def test_a_visible_post_below_hidden_ones_is_reattached_to_the_placeholder():
    rows = [_row("root", None, True),
            _row("a", "root", False, "4711"),
            _row("b", "a", False),
            _row("c", "b", True)]

    shown, _ = collapse(rows)

    assert [row for row in shown if row["url"] == "c"][0]["in_reply_to"] == "a"


def test_a_hidden_run_without_anything_visible_below_disappears_entirely():
    rows = [_row("root", None, True),
            _row("a", "root", False),
            _row("b", "a", False)]

    shown, placeholders = collapse(rows)

    assert [row["url"] for row in shown] == ["root"]
    assert placeholders == []


def test_two_separate_hidden_runs_get_one_placeholder_each():
    rows = [_row("root", None, True),
            _row("a", "root", False),
            _row("b", "a", True),
            _row("c", "root", False),
            _row("d", "c", True)]

    _, placeholders = collapse(rows)

    assert sorted(p["url"] for p in placeholders) == ["a", "c"]


def test_two_visible_branches_below_one_hidden_run_share_its_placeholder():
    rows = [_row("root", None, True),
            _row("a", "root", False),
            _row("b", "a", True),
            _row("c", "a", True)]

    shown, placeholders = collapse(rows)

    assert [p["url"] for p in placeholders] == ["a"]
    assert {row["in_reply_to"] for row in shown if row["url"] in ("b", "c")} == {"a"}


def test_a_visible_post_keeps_its_parent_when_nothing_is_hidden_above_it():
    rows = [_row("root", None, True), _row("a", "root", True)]

    shown, _ = collapse(rows)

    assert [row for row in shown if row["url"] == "a"][0]["in_reply_to"] == "root"


def _placeholder(**over):
    return {"mastodon_id": "4711",
            "url": "https://r/hidden",
            "emitted_at": "2026-10-01T12:00:00+00:00",
            "in_reply_to": "https://r/root",
            **over}


def test_a_placeholder_row_carries_the_instance_actor(domain):
    row = as_rows([_placeholder()])[0]

    assert row["actor_url"] == "https://example.com/actor"
    assert row["content"]["actor"] == "https://example.com/actor"


def test_a_placeholder_row_says_that_something_is_hidden(domain):
    assert as_rows([_placeholder()])[0]["content"]["status"]["content"] == HIDDEN_CONTENT


def test_a_placeholder_row_keeps_the_id_of_the_hidden_post(domain):
    row = as_rows([_placeholder()])[0]

    assert row["mastodon_id"] == "4711"
    assert row["content"]["mastodon_id"] == "4711"


def test_a_placeholder_row_hangs_below_its_visible_ancestor(domain):
    assert as_rows([_placeholder()])[0]["content"]["status"]["in_reply_to_id"] == "https://r/root"


def test_a_placeholder_row_is_dated_by_our_own_clock(domain):
    assert as_rows([_placeholder()])[0]["content"]["status"]["created_at"] == "2026-10-01T12:00:00+00:00"


def test_a_placeholder_row_is_not_a_boost(domain):
    assert as_rows([_placeholder()])[0]["kind"] == "content"

