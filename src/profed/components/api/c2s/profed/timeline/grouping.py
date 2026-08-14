# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


async def timeline_blocks(rows, after, limit, build_block):
    def identity(seen: set, row):
        ident = (row["root"], row["booster"])
        return (ident not in seen), (seen | {ident})

    async def try_emit_block(seen: set, row):
        new, seen = identity(seen, row)
        return seen, (await build_block(row) if new else None)

    async def skip_front(seen: set, row):
        nonlocal step
        if row["mastodon_id"] == after:
            step = try_emit_block
        return identity(seen, row)[1], None

    step = try_emit_block if after is None else skip_front

    async def make_all_blocks(seen, emitted):
        async for row in rows:
            seen, block = await step(seen, row)
            if block is not None:
                yield block
                emitted += 1
            if emitted >= limit:
                return

    async for block in make_all_blocks(set(), 0):
        yield block

