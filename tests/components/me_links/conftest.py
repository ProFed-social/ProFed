# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import timedelta
from profed.components.me_links import storage as storage_module
from profed.components.me_links import worker


CONFIG = {"min_wait": timedelta(days=1), "max_wait": timedelta(days=30), "ramp": timedelta(days=90)}


class FakeStorage:
    def __init__(self):
        self.links = {}
        self.verifications = {}

    async def replace_links(self, profile_url, link_urls):
        self.links[profile_url] = list(link_urls)

    async def forget_links(self, profile_url):
        self.links.pop(profile_url, None)

    async def links_of(self, profile_url):
        return list(self.links.get(profile_url, []))

    async def record_verification(self, profile_url, link_url, state, checked_at, stable_since,
                                  next_due_at, last_modified, etag, content_hash):
        self.verifications[(profile_url, link_url)] = {"profile_url": profile_url,
                                                       "link_url": link_url,
                                                       "state": state,
                                                       "checked_at": checked_at,
                                                       "stable_since": stable_since,
                                                       "next_due_at": next_due_at,
                                                       "last_modified": last_modified,
                                                       "etag": etag,
                                                       "content_hash": content_hash}

    async def forget_verification(self, profile_url, link_url):
        self.verifications.pop((profile_url, link_url), None)

    async def verification(self, profile_url, link_url):
        return self.verifications.get((profile_url, link_url))

    async def unchecked(self):
        return [{"profile_url": profile_url, "link_url": link_url}
                for profile_url, urls in self.links.items()
                for link_url in urls
                if (profile_url, link_url) not in self.verifications]

    async def due(self, now):
        return [dict(row, still_listed=row["link_url"] in self.links.get(row["profile_url"], []))
                for row in self.verifications.values()
                if row["next_due_at"] <= now]


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
    yield storage_module._instance
    storage_module._instance = backup_storage
    worker._workers = backup_workers

