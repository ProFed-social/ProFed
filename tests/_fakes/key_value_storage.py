# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


class FakeKeyValueStorage:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    async def ensure_schema(self):
        pass

    async def add(self, key, payload):
        self.rows[key] = dict(payload)

    async def upsert(self, key, payload):
        self.rows[key] = dict(payload)

    async def update(self, key, payload):
        self.rows[key] = {**self.rows.get(key, {}), **payload}

    async def delete(self, key, *_):
        self.rows.pop(key, None)

    async def fetch(self, key):
        return self.rows.get(key)

