# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.c2s.profed.timeline.grouping import timeline_blocks


def _row(mastodon_id, root, booster=None):
    return {"mastodon_id": mastodon_id, "root": root, "booster": booster}


async def _aiter(rows):
    for row in rows:
        yield row


async def _build(row):
    return {"trigger": row["mastodon_id"], "root": row["root"], "booster": row["booster"]}


async def _run(arows, after, limit):
    return [block async for block in timeline_blocks(arows, after, limit, _build)]


async def _triggers(rows, after, limit):
    return [block["trigger"] for block in await _run(_aiter(rows), after, limit)]


async def test_singles_are_each_emitted_once():
    assert await _triggers([_row(3, "c"), _row(2, "b"), _row(1, "a")], None, 20) == [3, 2, 1]


async def test_thread_parts_emit_once_at_the_newest_trigger():
    assert await _triggers([_row(3, "a"), _row(2, "a"), _row(1, "a")], None, 20) == [3]


async def test_same_thread_different_booster_are_separate_blocks():
    rows = [_row(9, "a", "X"), _row(2, "a", None), _row(1, "a", None)]
    blocks = await _run(_aiter(rows), None, 20)
    assert [(b["root"], b["booster"]) for b in blocks] == [("a", "X"), ("a", None)]


async def test_after_switches_to_emitting_and_prescan_suppresses_seen_threads():
    rows = [_row(5, "a"), _row(4, "b"), _row(3, "a"), _row(2, "c")]
    assert await _triggers(rows, 4, 20) == [2]


async def test_the_after_row_itself_is_not_re_emitted():
    assert await _triggers([_row(3, "c"), _row(2, "b"), _row(1, "a")], 2, 20) == [1]


async def test_limit_counts_blocks_and_stops_emission():
    assert await _triggers([_row(4, "d"), _row(3, "c"), _row(2, "b"), _row(1, "a")], None, 2) == [4, 3]


async def test_stops_when_iterable_is_exhausted_below_limit():
    assert await _triggers([_row(2, "b"), _row(1, "a")], None, 20) == [2, 1]


async def test_it_streams_without_consuming_the_whole_iterable():
    async def gen():
        yield _row(3, "c")
        raise AssertionError("should not be reached once limit is hit")

    blocks = await _run(gen(), None, 1)
    assert [block["trigger"] for block in blocks] == [3]


async def test_a_block_that_build_returns_none_for_is_skipped():
    async def build(row):
        return None if row["root"] == "x" else {"trigger": row["mastodon_id"]}

    rows = [_row(3, "x"), _row(2, "a"), _row(1, "b")]
    blocks = [block async for block in timeline_blocks(_aiter(rows), None, 20, build)]
    assert [block["trigger"] for block in blocks] == [2, 1]

