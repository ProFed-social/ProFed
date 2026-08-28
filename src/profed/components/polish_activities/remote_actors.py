# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import remote_actors as topic
from profed.util import noop
from .update_waiting import update_all_waiting
from .storage import storage


logger = logging.getLogger(__name__)


async def _discovered(object_id: str, payload: dict, sequence_id: int) -> None:
    await (await storage()).remember_actor(payload["acct"], payload["actor_url"])
    for acct in [payload["acct"], *(payload.get("acct_aliases") or [])]:
        await update_all_waiting(acct, sequence_id)


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"discovered": _discovered},
                                             event_handler_signature=with_sequence_id)

