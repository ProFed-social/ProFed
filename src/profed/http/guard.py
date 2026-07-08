# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import ipaddress
import httpx


_NAT64 = ipaddress.ip_network("64:ff9b::/96")


class BlockedAddressError(Exception):
    pass


def _embedded_ipv4(ip):
    return (ip.ipv4_mapped or
            ip.sixtofour or
            (ipaddress.IPv4Address(int(ip) & 0xffffffff) if ip in _NAT64 else None))


def _blocked_ip(ip):
    embedded = _embedded_ipv4(ip) if isinstance(ip, ipaddress.IPv6Address) else None
    return _blocked_ip(embedded) if embedded is not None else not ip.is_global


async def _assert_public(host):
    infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    for info in infos:
        if _blocked_ip(ipaddress.ip_address(info[4][0])):
            raise BlockedAddressError(host)


class GuardTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        await _assert_public(request.url.host)
        return await super().handle_async_request(request)

