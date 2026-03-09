# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from fastapi.testclient import TestClient
from profed.components.api.app import create_app


def test_webfinger_success():
    app = create_app(None, None)
    client = TestClient(app)

    response = client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:alice@example.com"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["subject"] == "acct:alice@example.com"
    assert data["links"][0]["rel"] == "self"
    assert data["links"][0]["type"] == "application/activity+json"
    assert data["links"][0]["href"] == "https://example.com/users/alice"


def test_webfinger_invalid_resource():
    app = create_app(None, None)
    client = TestClient(app)

    response = client.get(
        "/.well-known/webfinger",
        params={"resource": "invalid"},
    )

    assert response.status_code == 404
