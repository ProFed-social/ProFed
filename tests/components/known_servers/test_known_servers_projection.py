# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from profed.components.known_servers import projection


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)

HOST = "pleroma.test"


def _payload(**rest):
    return {"checked_at": NOW.isoformat(), "stable_since": NOW.isoformat(), **rest}


@pytest.mark.asyncio
async def test_a_discovered_host_is_remembered(component):
    await projection._discovered(HOST, {})

    assert component.hosts == {HOST}


@pytest.mark.asyncio
async def test_an_update_records_the_check(component):
    await projection._checked(HOST, _payload(etag='"a"'))

    assert component.checks[HOST]["checked_at"] == NOW
    assert component.checks[HOST]["etag"] == '"a"'
    assert component.checks[HOST]["failures"] == 0


@pytest.mark.asyncio
async def test_a_stable_host_is_asked_again_later_than_a_fresh_one(component):
    await projection._checked(HOST, _payload(stable_since=(NOW - timedelta(days=90)).isoformat()))
    patient = component.checks[HOST]["next_due_at"]

    await projection._checked(HOST, _payload())

    assert component.checks[HOST]["next_due_at"] < patient


@pytest.mark.asyncio
async def test_a_failed_check_keeps_its_failure_count(component):
    await projection._checked(HOST, _payload(failures=2))

    assert component.checks[HOST]["failures"] == 2


@pytest.mark.asyncio
async def test_a_lost_host_is_no_longer_scheduled(component):
    await projection._discovered(HOST, {})

    await projection._lost(HOST, {})

    assert component.hosts == set()


@pytest.mark.asyncio
async def test_a_lost_host_keeps_what_was_known_about_it(component):
    await projection._checked(HOST, _payload(etag='"a"'))

    await projection._lost(HOST, {})

    assert component.checks[HOST]["etag"] == '"a"'

