# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import partial
from profed.identity import actor_url_from_username
from profed.models.mastodon import placeholder_account
from profed.components.api.c2s.shared.known_accounts.service import cached_multiple
from profed.components.api.c2s.shared.statuses import as_objects, user_timeline
from profed.components.api.c2s.shared.statuses.service import make_statuses
from profed.components.api.c2s.profed.timeline.grouping import timeline_blocks


async def _build_block(row, viewer):
    part_rows = await (await as_objects.storage()).thread_of(row["root"])
    if not part_rows:
        return None
    parts = await make_statuses(part_rows, viewer)
    booster = None
    boosted = set()
    if row["booster"] is not None:
        highlighted = set(await (await as_objects.storage())
                          .boosted_parts(row["booster"], [part["url"] for part in part_rows]))
        boosted = {part.id
                   for part_row, part in zip(part_rows, parts)
                   if part_row["url"] in highlighted}
        accounts = await cached_multiple([row["booster"]])
        booster = accounts.get(row["booster"]) or placeholder_account(row["booster"])
    return {"parts": parts, "booster": booster, "boosted": boosted, "cursor": row["mastodon_id"]}


async def timeline(username, after=None, limit=20):
    return timeline_blocks((await user_timeline.storage()).thread_roots(username),
                           after,
                           limit,
                           partial(_build_block, viewer=actor_url_from_username(username)))

