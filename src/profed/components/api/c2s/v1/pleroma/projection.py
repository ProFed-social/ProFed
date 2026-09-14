# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection, with_event_type
from profed.topics import activities
from profed.util import noop
from .storage import storage


REACTION_VERBS = ("Like", "EmojiReact")


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _remembered(event_type: str, object_id: str, payload: dict) -> None:
    await (await storage()).remember(object_id, event_type)


async def _forgotten(event_type: str, object_id: str, payload: dict) -> None:
    undone = payload["activity"].get("object")
    if isinstance(undone, dict) and undone.get("type") in REACTION_VERBS:
        await (await storage()).forget(undone.get("id"))


handle_events, rebuild, _ = build_projection(topic=activities,
                                             init=_init,
                                             on_snapshot_item=noop,
                                             on_message_type={**{verb: _remembered for verb in REACTION_VERBS},
                                                              "Undo": _forgotten},
                                             event_handler_signature=with_event_type)

