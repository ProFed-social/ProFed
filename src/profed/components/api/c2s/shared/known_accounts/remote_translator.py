# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import remote_actors
from .service import make_account


logger = logging.getLogger(__name__)
_REMOTE_ACTORS_SOURCE = source_key("remote_actors")


async def _noop() -> None:
    pass


async def _noop_item(item: dict) -> None:
    pass


async def _discovered(object_id, payload, sequence_id) -> None:
    account = make_account(payload)
    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="updated",
                      object_id=object_id,
                      payload=account.model_dump(),
                      message_id=_REMOTE_ACTORS_SOURCE.message_id(sequence_id))


handle_events, rebuild, _ = build_projection(topic=remote_actors,
                                             subscriber="c2s_known_accounts_remote",
                                             init=_noop,
                                             on_snapshot_item=_noop_item,
                                             on_message_type={"discovered": _discovered},
                                             event_handler_signature=with_sequence_id)

