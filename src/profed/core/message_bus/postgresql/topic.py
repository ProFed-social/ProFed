# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, AsyncGenerator
from asyncpg import Pool
from .publisher import Publisher
from .snapshot import SnapshotPublisher
from .subscriber import subscribe

class Topic:
    def __init__(self, pool: Pool, config: Dict[str, str], name: str):
        self._pool = pool
        self._config = config
        self._name = name

    def publish(self) -> Publisher:
        return Publisher(self._pool, self._config["schema"], self._name)

    def publish_snapshot(self) -> SnapshotPublisher:
        return SnapshotPublisher(self._pool, self._config["schema"], self._name)

    def subscribe(self, component_schema: str) -> AsyncGenerator[Dict[str, str], None]:
        return subscribe(self._pool, self._config, self._name, component_schema)
