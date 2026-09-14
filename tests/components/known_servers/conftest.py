# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import timedelta
from profed.components.known_servers import storage as storage_module
from profed.components.known_servers import projection, worker


CONFIG = {"min_wait": timedelta(days=1),
          "max_wait": timedelta(days=30),
          "ramp": timedelta(days=90),
          "give_up_after": 3}


class FakeStorage:
    def __init__(self):
        self.hosts = set()
        self.checks = {}

    async def remember_host(self, host):
        self.hosts.add(host)

    async def forget_host(self, host):
        self.hosts.discard(host)

    async def record_check(self, host, checked_at, stable_since, next_due_at,
                           failures, last_modified, etag, content_hash):
        self.checks[host] = {"host": host,
                             "checked_at": checked_at,
                             "stable_since": stable_since,
                             "next_due_at": next_due_at,
                             "failures": failures,
                             "last_modified": last_modified,
                             "etag": etag,
                             "content_hash": content_hash}

    async def check_of(self, host):
        return self.checks.get(host)

    async def unchecked(self):
        return [{"host": host} for host in sorted(self.hosts) if host not in self.checks]

    async def due(self, now):
        return [{"host": row["host"]}
                for row in self.checks.values()
                if row["next_due_at"] <= now and row["host"] in self.hosts]


class FakeWorkers:
    def __init__(self):
        self.submitted = []

    def submit(self, key, item=None):
        self.submitted.append(key)

    def start(self):
        return None


@pytest.fixture
def component():
    backup_storage = storage_module._instance
    backup_workers = worker._workers
    storage_module._instance = FakeStorage()
    worker._workers = FakeWorkers()
    worker.configure(dict(CONFIG))
    projection.configure(dict(CONFIG))
    yield storage_module._instance
    storage_module._instance = backup_storage
    worker._workers = backup_workers

