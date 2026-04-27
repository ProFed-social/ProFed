# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import base64
import hashlib
import json
import pytest
 
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
 
from profed.http.signatures import generate_key_pair, sign_request


URL    = "https://remote.example/inbox/alice"
KEY_ID = "https://example.com/actors/bob#main-key"
BODY   = json.dumps({"type": "Create"}).encode()


@pytest.fixture(scope="module")
def key_pair():
    return generate_key_pair()


@pytest.fixture(scope="module")
def signed_headers(key_pair):
    _, private_pem = key_pair
    return sign_request("POST", URL, BODY, KEY_ID, private_pem)
 
 
def test_generate_key_pair_returns_pem_strings(key_pair):
    public_pem, private_pem = key_pair
    assert public_pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert private_pem.startswith("-----BEGIN PRIVATE KEY-----")
 
 
def test_generate_key_pair_produces_valid_key_pair(key_pair):
    public_pem, private_pem = key_pair
    private_key = serialization.load_pem_private_key(private_pem.encode(),
                                                     password=None)
    derived_public = \
            private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM,
                                                  format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    assert derived_public == public_pem
 
 
def test_generate_key_pair_unique():
    pub1, priv1 = generate_key_pair()
    pub2, priv2 = generate_key_pair()

    assert pub1 != pub2
    assert priv1 != priv2
 
 
def test_sign_request_returns_required_headers(signed_headers):
    assert "Date"      in signed_headers
    assert "Digest"    in signed_headers
    assert "Signature" in signed_headers
 
 
def test_sign_request_digest_matches_body(signed_headers):
    expected = "SHA-256=" + base64.b64encode(hashlib.sha256(BODY).digest()).decode()
    assert signed_headers["Digest"] == expected

 
def test_sign_request_signature_verifiable(key_pair, signed_headers):
    public_pem, _ = key_pair
    signed_string = (f"(request-target): post /inbox/alice\n"
                     f"host: remote.example\n"
                     f"date: {signed_headers['Date']}\n"
                     f"digest: {signed_headers['Digest']}")
    sig_bytes  = base64.b64decode(signed_headers["Signature"].split('signature="')[1].rstrip('"'))
    public_key = serialization.load_pem_public_key(public_pem.encode())

    public_key.verify(sig_bytes, signed_string.encode(), padding.PKCS1v15(), hashes.SHA256())

 
def test_sign_request_signature_contains_key_id(signed_headers):
    assert KEY_ID in signed_headers["Signature"]

