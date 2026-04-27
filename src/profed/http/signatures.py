# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import base64
import hashlib
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlparse
 
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.asymmetric import rsa
 
 
def generate_key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()).decode()

    return public_pem, private_pem
 
 
def sign_request(method: str,
                 url: str,
                 body: bytes,
                 key_id: str,
                 private_key_pem: str) -> dict[str, str]:
    parsed = urlparse(url)
    host   = parsed.netloc
    path   = parsed.path or "/"
    date   = format_datetime(datetime.now(timezone.utc), usegmt=True)
    digest = "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()
 
    signed_string = (f"(request-target): {method.lower()} {path}\n"
                     f"host: {host}\n"
                     f"date: {date}\n"
                     f"digest: {digest}")
 
    private_key: RSAPrivateKey = \
            serialization.load_pem_private_key(private_key_pem.encode(),
                                               password=None)
    signature_bytes = private_key.sign(signed_string.encode(),
                                       padding.PKCS1v15(),
                                       hashes.SHA256())
    signature_b64 = base64.b64encode(signature_bytes).decode()
 
    signature_header = (f'keyId="{key_id}",algorithm="rsa-sha256",'
                        f'headers="(request-target) host date digest",'
                        f'signature="{signature_b64}"')
 
    return {"Date":      date,
            "Digest":    digest,
            "Signature": signature_header}

