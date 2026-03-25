# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

# src/profed/core/message_bus/source_key.py

import uuid


_SOURCE_KEYS = {
    "users": "users"
}


class SourceKey:
    def __init__(self, source_topic: str):
        global _SOURCE_KEYS

        source_key = _SOURCE_KEYS.get(source_topic)
        if source_key is None:
            raise ValueError("source_topic has no mapping to source key")

        source_id = (source_key.rjust(8, "\0")
                     if len(source_key) < 8
                     else source_key).encode("ascii", "strict")
        if len(source_id) != 8:
            raise ValueError("source_id must be exactly 8 bytes")

        self._prefix = source_id

    def message_id(self, message_id: int) -> uuid.UUID:
        if message_id < 0:
            raise ValueError("message_id must be non-negative")
        return uuid.UUID(bytes=self._prefix + message_id.to_bytes(8, "big", signed=False))


def source_key(source_id: str) -> SourceKey:
    return SourceKey(source_id)

