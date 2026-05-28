# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import uuid


class SourceKey:
    def __init__(self, source_topic: str):
        self._prefix = hashlib.sha256(source_topic.encode("utf-8")).digest()[:8]

    def message_id(self, sequence_id: int) -> uuid.UUID:
        if sequence_id < 0:
            raise ValueError("sequence_id must be non-negative")
        return uuid.UUID(bytes=self._prefix + sequence_id.to_bytes(8, "big", signed=False))


def source_key(source_topic: str) -> SourceKey:
    return SourceKey(source_topic)

