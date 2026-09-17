# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.profed.timeline import router as timeline_module


CLAIMS = {"preferred_username": "alice", "sub": "alice"}


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(timeline_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


async def _blocks(*cursors):
    for cursor in cursors:
        yield {"parts": [], "booster": None, "boosted": set(), "cursor": cursor}


def _service(*cursors):
    return patch.object(timeline_module.service, "timeline", AsyncMock(return_value=_blocks(*cursors)))


def test_the_timeline_reports_a_block_per_cursor(client):
    with _service(500, 400):
        response = client.get("/timeline")

    assert response.status_code == 200
    assert [block["cursor"] for block in response.json()] == ["500", "400"]


def test_the_timeline_points_at_the_next_page(client):
    with _service(500, 400):
        response = client.get("/timeline")

    assert 'max_id=400>; rel="next"' in response.headers["Link"]


def test_an_empty_timeline_has_no_link_header(client):
    with _service():
        response = client.get("/timeline")

    assert "Link" not in response.headers


def test_the_cursor_reaches_the_service_as_a_number(client):
    with _service() as timeline:
        client.get("/timeline?max_id=400&limit=7")

    timeline.assert_awaited_once_with("alice", max_id=400, limit=7)


def test_without_a_cursor_the_service_gets_none(client):
    with _service() as timeline:
        client.get("/timeline")

    timeline.assert_awaited_once_with("alice", max_id=None, limit=20)


def test_a_limit_beyond_the_ceiling_is_refused(client):
    with _service():
        assert client.get("/timeline?limit=100").status_code == 422

