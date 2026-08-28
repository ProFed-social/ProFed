# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from urllib.parse import urlparse


def domain_of(acct: str) -> str:
    return acct.rsplit("@", 1)[1] if "@" in acct else ""


def host_of(url: str) -> str:
    return urlparse(url).netloc

