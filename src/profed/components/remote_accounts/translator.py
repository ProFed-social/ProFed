# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import remote_actors
from profed.models.mastodon import Account
from profed.util import noop


logger = logging.getLogger(__name__)
_REMOTE_ACTORS_SOURCE = source_key("remote_actors")


async def _discovered(object_id, payload, sequence_id) -> None:
    account = Account.from_actor(payload.get("actor_data") or {},
                                 acct=payload["acct"],
                                 url=payload["actor_url"],
                                 created_at=payload.get("created_at"))

    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="updated",
                      object_id=object_id,
                      payload=account.model_dump(),
                      message_id=_REMOTE_ACTORS_SOURCE.message_id(sequence_id))


handle_events, rebuild, _ = build_projection(topic=remote_actors,
                                             subscriber="remote_accounts",
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"discovered": _discovered},
                                             event_handler_signature=with_sequence_id)

