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
 
    return {"Host":      host,
            "Date":      date,
            "Digest":    digest,
            "Signature": signature_header}


def _parse_signature_header(header: str) -> dict:
    return {key.strip(): value.strip().strip('"')
            for key, _, value in (part.strip().partition("=")
                                  for part in header.split(","))}


def key_id_from_signature_header(header: str) -> str | None:
    key_id = _parse_signature_header(header).get("keyId")

    return key_id.split("#")[0] if key_id is not None else None


def verify_request(method:         str,
                   path:           str,
                   headers:        dict,
                   body:           bytes,
                   public_key_pem: str) -> bool:
    h = {k.lower(): v for k, v in headers.items()}

    sig_header = h.get("signature", "")
    if not sig_header:
        return False

    params        = _parse_signature_header(sig_header)
    headers_list  = params.get("headers", "date").split()

    signature_b64 = params.get("signature")
    if not signature_b64:
        return False

    if "digest" in headers_list:
        expected = "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()
        if h.get("digest", "") != expected:
            return False

    parts = []
    for hdr in headers_list:
        if hdr == "(request-target)":
            parts.append(f"(request-target): {method.lower()} {path}")
        else:
            value = h.get(hdr)
            if value is None:
                return False
            parts.append(f"{hdr}: {value}")

    signed_string = "\n".join(parts)

    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        public_key.verify(base64.b64decode(signature_b64),
                          signed_string.encode(),
                          padding.PKCS1v15(),
                          hashes.SHA256())

        return True
    except Exception:
        return False

