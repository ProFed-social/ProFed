# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import base64
import hashlib
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlparse
 
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.asymmetric import rsa
 
 
def generate_key_pair() -> tuple[str, str]:
    def _pair_as_pem(private_key):
        return (private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM,
                                                      format=serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
                private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                          format=serialization.PrivateFormat.PKCS8,
                                          encryption_algorithm=serialization.NoEncryption()).decode())

    return _pair_as_pem(rsa.generate_private_key(public_exponent=65537, key_size=2048))

 
def sign_request(method: str, url: str, body: bytes, key_id: str, private_key_pem: str) -> dict[str, str]:
    def _extract_url_parts(url):
        parsed = urlparse(url)
        return parsed.netloc, (parsed.path or "/")

    def _covered(date, digest, host, path):
        return ({"Host": host,
                 "Date": date,
                 **({"Digest": digest} if digest else  {})},
                 ([("(request-target)", f"{method.lower()} {path}"), ("host", host), ("date", date)] +
                  ([("digest", digest)] if digest else [])))

    def _signature(private_key_pem, result, covered):
        def _private_key(private_key_pem) -> RSAPrivateKey:
            return serialization.load_pem_private_key(private_key_pem.encode(), password=None)

        def _signature(covered, private_key_pem):
            return base64.b64encode(_private_key(private_key_pem).sign("\n".join(f"{name}: {value}"
                                                                                 for name, value in covered).encode(),
                                                                       padding.PKCS1v15(),
                                                                       hashes.SHA256())).decode()
     
        return ({"Signature": (f'keyId="{key_id}",algorithm="rsa-sha256",'
                               f'headers="{" ".join(name for name, _ in covered)}",'
                               f'signature="{_signature(covered, private_key_pem)}"'),
                 **result})


    return _signature(private_key_pem,
                      *_covered(format_datetime(datetime.now(timezone.utc), usegmt=True),
                                (("SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode())
                                 if body else
                                 None),
                                *(_extract_url_parts(url))))


def make_sign(key_id: str, private_key_pem: str):
    def sign(request):
        request.headers.update(sign_request(request.method, str(request.url), request.content, key_id, private_key_pem))
        return request
    return sign


def _parse_signature_header(header: str) -> dict:
    return {key.strip(): value.strip().strip('"')
            for key, _, value in (part.strip().partition("=") for part in header.split(","))}


def key_id_from_signature_header(header: str) -> str | None:
    key_id = _parse_signature_header(header).get("keyId")

    return key_id.split("#")[0] if key_id is not None else None


def verify_request(method: str, path: str, headers: dict, body: bytes, public_key_pem: str) -> bool:
    def _normalized_headers(headers: dict) -> dict:
        return {k.lower(): v for k, v in headers.items()}

    def _sig_header(h, and_then):
        def _sh():
            sig_header = h.get("signature", "")
            return and_then(h, sig_header) if sig_header else False
        return _sh
     
    def _signature(and_then):
        def _sig(h, sig_header):
            params = _parse_signature_header(sig_header)
            signature_b64 = params.get("signature")
            return and_then(h, params.get("headers", "date").split(), signature_b64) if signature_b64 else False
        return _sig

    def _digest(body, and_then):
        def _d(h, headers_list, signature_b64):
            if "digest" in headers_list:
                expected = "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()
                if h.get("digest", "") != expected:
                    return False

            return and_then(h, headers_list, signature_b64)
        return _d

    def _request_target(method, path, and_then):
        def _rt(h, headers_list, signature_b64):
            parts = [f"(request-target): {method.lower()} {path}"
                     if hdr == "(request-target)"  else
                     [None if value is None else f"{hdr}: {value}" for value in (h.get(hdr), )][0]
                     for hdr in headers_list]
            return False if any(p is None for p in parts) else and_then(signature_b64, "\n".join(parts))
        return _rt

    def _verify_signature(public_key_pem):
        def _vs(signature_b64, signed_string):
            try:
                public_key: RSAPublicKey = serialization.load_pem_public_key(public_key_pem.encode())
                public_key.verify(base64.b64decode(signature_b64),
                                  signed_string.encode(),
                                  padding.PKCS1v15(),
                                  hashes.SHA256())

                return True
            except Exception:
                return False
        return _vs

    return _sig_header(_normalized_headers(headers),
                       and_then=_signature(and_then=_digest(body,
                                                            and_then=_request_target(method,
                                                                                     path,
                                                                                     and_then=_verify_signature(public_key_pem)))))()

