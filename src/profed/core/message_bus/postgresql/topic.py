# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, AsyncGenerator
from asyncpg import Pool
from .publisher import Publisher
from .snapshot import SnapshotPublisher, last_snapshot
from .subscriber import subscribe

class Topic:
    def __init__(self, component_name: str, pool: Pool, config: Dict[str, str], name: str):
        self._pool = pool
        self._config = config
        self._name = name
        self._component_name = component_name

    def publish(self) -> Publisher:
        return Publisher(self._pool, self._config["schema"], self._name)

    def publish_snapshot(self) -> SnapshotPublisher:
        return SnapshotPublisher(self._pool, self._config["schema"], self._name)

    def subscribe(self, last_seen: int = 0, include_sequence_id: bool = False) -> AsyncGenerator[Dict[str, str], None]:
        return subscribe(self._pool, self._config, self._name, self._component_name, last_seen, include_sequence_id)

    def last_snapshot(self):
        return last_snapshot(self._pool, self._config["schema"], self._name)
