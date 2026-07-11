# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import httpx
from profed.http.signatures import sign_request, verify_request, generate_key_pair, make_sign


def test_get_is_signed_without_digest():
    _, private = generate_key_pair()

    headers = sign_request("GET", "https://example.com/actor", b"",
                           "https://me.example/actor#main-key", private)

    assert "Digest" not in headers
    assert 'headers="(request-target) host date"' in headers["Signature"]


def test_post_is_signed_with_digest():
    _, private = generate_key_pair()

    headers = sign_request("POST", "https://example.com/inbox", b"hello",
                           "https://me.example/actor#main-key", private)

    assert "Digest" in headers
    assert 'headers="(request-target) host date digest"' in headers["Signature"]


def test_signed_get_round_trips_through_verify():
    public, private = generate_key_pair()

    headers = sign_request("GET", "https://example.com/actor", b"",
                           "https://me.example/actor#main-key", private)

    assert verify_request("GET", "/actor", headers, b"", public)


def test_signed_post_round_trips_through_verify():
    public, private = generate_key_pair()

    headers = sign_request("POST", "https://example.com/inbox", b"hello",
                           "https://me.example/actor#main-key", private)

    assert verify_request("POST", "/inbox", headers, b"hello", public)


def test_make_sign_produces_verifiable_signature():
    public_pem, private_pem = generate_key_pair()
    request = httpx.Request("GET", "https://remote.example/actors/bob")
    signed = make_sign("https://me.example/actor#main-key", private_pem)(request)

    assert verify_request("GET", "/actors/bob", dict(signed.headers), signed.content, public_pem)

