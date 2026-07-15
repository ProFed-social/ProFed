# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import accounts
from profed.identity import acct_from_username, account_id
from profed.util import noop


logger = logging.getLogger(__name__)
_ACCOUNTS_SOURCE = source_key("accounts")

_VERBS = ("created", "updated", "followers_changed", "following_changed",
          "statuses_changed", "deleted")


async def _forward(event_type: str, username: str, payload: dict, sequence_id: int) -> None:
    aid = str(int(account_id(acct_from_username(username))))
    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type=event_type,
                      object_id=aid,
                      payload=payload,
                      message_id=_ACCOUNTS_SOURCE.message_id(sequence_id))


def _forwarder(event_type: str):
    async def _handle(object_id, payload, sequence_id) -> None:
        await _forward(event_type, object_id, payload, sequence_id)
    return _handle


handle_events, rebuild, _ = build_projection(topic=accounts,
                                             subscriber="local_accounts",
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={verb: _forwarder(verb)
                                                              for verb in _VERBS},
                                             event_handler_signature=with_sequence_id)

