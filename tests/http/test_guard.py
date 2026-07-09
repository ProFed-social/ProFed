# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import ipaddress
import httpx
import pytest

from unittest.mock import AsyncMock, patch
from profed.http.guard import _blocked_ip, _assert_public, BlockedAddressError, GuardTransport
from profed.http.client import HttpClient


def _b(addr):
    return _blocked_ip(ipaddress.ip_address(addr))


def test_blocks_private_ranges():
    assert _b("10.0.0.1") and _b("192.168.1.1") and _b("172.16.0.1")


def test_blocks_loopback_link_local_and_metadata():
    assert _b("127.0.0.1") and _b("169.254.169.254") and _b("fe80::1")


def test_blocks_cgnat_ula_and_v6_loopback():
    assert _b("100.64.0.1") and _b("fc00::1") and _b("::1")


def test_allows_public_v4_and_v6():
    assert not _b("93.184.216.34")
    assert not _b("2606:2800:220:1:248:1893:25c8:1946")


def test_unpacks_ipv4_mapped_ipv6():
    assert _b("::ffff:10.0.0.1")
    assert not _b("::ffff:93.184.216.34")


def test_unpacks_nat64_embedded_ipv4():
    assert _b("64:ff9b::a00:1")


def _infos(*ips):
    return [(None, None, None, None, (ip, 0)) for ip in ips]


@pytest.mark.asyncio
async def test_assert_public_raises_on_private():
    with patch("profed.http.guard.asyncio.get_running_loop") as loop:
        loop.return_value.getaddrinfo = AsyncMock(return_value=_infos("10.0.0.1"))
        with pytest.raises(BlockedAddressError):
            await _assert_public("evil.example")


@pytest.mark.asyncio
async def test_assert_public_passes_for_public():
    with patch("profed.http.guard.asyncio.get_running_loop") as loop:
        loop.return_value.getaddrinfo = AsyncMock(return_value=_infos("93.184.216.34"))
        await _assert_public("example.com")


@pytest.mark.asyncio
async def test_assert_public_blocks_when_any_resolved_ip_is_private():
    with patch("profed.http.guard.asyncio.get_running_loop") as loop:
        loop.return_value.getaddrinfo = AsyncMock(return_value=_infos("93.184.216.34", "10.0.0.1"))
        with pytest.raises(BlockedAddressError):
            await _assert_public("mixed.example")


@pytest.mark.asyncio
async def test_transport_validates_before_super():
    request = httpx.Request("GET", "http://10.0.0.1/")
    with pytest.raises(BlockedAddressError):
        await GuardTransport().handle_async_request(request)


@pytest.mark.asyncio
async def test_http_client_blocks_private_target():
    with pytest.raises(BlockedAddressError):
        await HttpClient().get("http://169.254.169.254/latest/meta-data/")


@pytest.mark.asyncio
async def test_transport_validates_each_host_once_per_redirect_chain():
    seen = []
    resolved = []

    async def _super(self, request):
        seen.append(request.url.host)
        if len(seen) == 1:
            return httpx.Response(302, headers={"location": "/foo"}, request=request)
        return httpx.Response(200, request=request)

    def _getaddrinfo(host, port):
        resolved.append(host)
        return _infos("93.184.216.34")

    with patch("profed.http.guard.asyncio.get_running_loop") as loop:
        loop.return_value.getaddrinfo = AsyncMock(side_effect=_getaddrinfo)
        with patch.object(httpx.AsyncHTTPTransport, "handle_async_request", _super):
            async with httpx.AsyncClient(transport=GuardTransport(),
                                         follow_redirects=True) as client:
                await client.get("http://example.com/")

    assert seen == ["example.com", "example.com"]
    assert resolved == ["example.com"]

