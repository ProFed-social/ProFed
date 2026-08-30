# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from profed.components.me_links import projection
from profed.topics.me_links_topic import CHECK_STATES


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)

CONFIG = {"min_wait": timedelta(days=1), "max_wait": timedelta(days=30), "ramp": timedelta(days=90)}

PROFILE = "https://p.test/@alice"
LINK = "https://a.test/"
EDGE = f"{PROFILE}|{LINK}"


@pytest.fixture(autouse=True)
def configured():
    projection.configure(dict(CONFIG))


def _payload(checked_at=NOW, stable_since=NOW, **rest):
    return dict({"checked_at": checked_at.isoformat(), "stable_since": stable_since.isoformat()}, **rest)


@pytest.mark.asyncio
async def test_a_verified_event_becomes_a_row(component):
    await projection._checked("verified")(EDGE, _payload())

    assert (await component.verification(PROFILE, LINK))["state"] == "verified"


@pytest.mark.asyncio
async def test_an_unverified_event_becomes_a_row(component):
    await projection._checked("unverified")(EDGE, _payload())

    assert (await component.verification(PROFILE, LINK))["state"] == "unverified"


@pytest.mark.asyncio
async def test_a_gone_event_becomes_a_row(component):
    await projection._checked("gone")(EDGE, _payload())

    assert (await component.verification(PROFILE, LINK))["state"] == "gone"


@pytest.mark.asyncio
async def test_the_freshness_headers_are_kept(component):
    await projection._checked("verified")(EDGE, _payload(etag='"abc"', content_hash="hash"))

    stored = await component.verification(PROFILE, LINK)

    assert stored["etag"] == '"abc"'
    assert stored["content_hash"] == "hash"


@pytest.mark.asyncio
async def test_a_fresh_page_is_due_after_the_minimum(component):
    await projection._checked("verified")(EDGE, _payload())

    assert (await component.verification(PROFILE, LINK))["next_due_at"] == NOW + timedelta(days=1)


@pytest.mark.asyncio
async def test_a_stable_page_is_due_much_later(component):
    await projection._checked("verified")(EDGE, _payload(stable_since=NOW - timedelta(days=60)))

    assert (await component.verification(PROFILE, LINK))["next_due_at"] > NOW + timedelta(days=15)


@pytest.mark.asyncio
async def test_a_later_event_replaces_the_earlier_one(component):
    await projection._checked("verified")(EDGE, _payload())

    await projection._checked("unverified")(EDGE, _payload(checked_at=NOW + timedelta(days=2)))

    assert (await component.verification(PROFILE, LINK))["state"] == "unverified"


@pytest.mark.asyncio
async def test_a_deleted_event_removes_the_row(component):
    await projection._checked("verified")(EDGE, _payload())

    await projection._deleted(EDGE, {})

    assert await component.verification(PROFILE, LINK) is None


@pytest.mark.asyncio
async def test_deleting_an_unknown_row_is_harmless(component):
    await projection._deleted(EDGE, {})

    assert await component.verification(PROFILE, LINK) is None


def test_every_check_result_has_a_handler():
    assert set(projection.HANDLERS) >= CHECK_STATES


def test_the_deletion_has_a_handler():
    assert "deleted" in projection.HANDLERS

