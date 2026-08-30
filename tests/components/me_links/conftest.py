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
        self.profiles = {}
        self.verifications = {}

    async def replace_links(self, actor_url, profile_url, link_urls):
        self.links[actor_url] = list(link_urls)
        self.profiles[actor_url] = profile_url

    async def forget_links(self, actor_url):
        self.links.pop(actor_url, None)
        self.profiles.pop(actor_url, None)

    async def links_of(self, actor_url):
        return list(self.links.get(actor_url, []))

    async def record_verification(self,
                                  actor_url,
                                  link_url,
                                  state,
                                  checked_at,
                                  stable_since,
                                  next_due_at,
                                  last_modified,
                                  etag,
                                  content_hash):
        self.verifications[(actor_url, link_url)] = {"actor_url": actor_url,
                                                     "link_url": link_url,
                                                     "state": state,
                                                     "checked_at": checked_at,
                                                     "stable_since": stable_since,
                                                     "next_due_at": next_due_at,
                                                     "last_modified": last_modified,
                                                     "etag": etag,
                                                     "content_hash": content_hash}

    async def forget_verification(self, actor_url, link_url):
        self.verifications.pop((actor_url, link_url), None)

    async def verification(self, actor_url, link_url):
        return self.verifications.get((actor_url, link_url))

    async def unchecked(self):
        return [{"actor_url": actor_url, "profile_url": self.profiles.get(actor_url), "link_url": link_url}
                for actor_url, urls in self.links.items()
                for link_url in urls
                if (actor_url, link_url) not in self.verifications]

    async def due(self, now):
        return [dict(row,
                     profile_url=self.profiles.get(row["actor_url"]),
                     still_listed=row["link_url"] in self.links.get(row["actor_url"], []))
                for row in self.verifications.values()
                if row["next_due_at"] <= now]


class FakeWorkers:
    def __init__(self):
        self.submitted = []
        self.items = []

    def submit(self, key, item=None):
        self.submitted.append(key)
        self.items.append(item)

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

