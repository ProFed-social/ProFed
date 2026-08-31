# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.s2s.actor.router import router as actor_router
from profed.components.api.s2s.instance_actor.router import router as instance_actor_router
from profed.components.api.s2s.nodeinfo.router import router as nodeinfo_router
from profed.components.api.s2s.outbox.router import router as outbox_router
from profed.components.api.s2s.webfinger.router import router as webfinger_router


ROUTERS = (actor_router, instance_actor_router, nodeinfo_router, outbox_router, webfinger_router)


def _walk(routes):
    for route in routes:
        yield route
        yield from _walk(getattr(route, "routes", ()))


def _routes():
    return [route
            for router in ROUTERS
            for route in _walk(router.routes)
            if "GET" in (getattr(route, "methods", None) or ())]


@pytest.mark.parametrize("route", _routes(), ids=lambda route: route.path)
def test_every_readable_route_answers_head(route):
    assert "HEAD" in route.methods


def test_a_head_request_gets_no_body():
    app = FastAPI()
    app.include_router(nodeinfo_router)

    response = TestClient(app, raise_server_exceptions=False).head("/.well-known/nodeinfo")

    assert response.status_code == 200
    assert response.content == b""

