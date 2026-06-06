# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components import api


async def test_api_does_not_require_proxy_token(monkeypatch):
    inited = []

    async def _fake_init(config, deactivate):
        inited.append(deactivate)

    monkeypatch.setattr(api.s2s, "init", _fake_init)
    monkeypatch.setattr(api.c2s, "init", _fake_init)
    await api.Api({})
    assert len(inited) == 2


async def test_mount_endpoints_mounts_both(monkeypatch):
    mounted = []

    def _fake_mount(app, deactivate):
        mounted.append(app)

    monkeypatch.setattr(api.s2s, "mount_routers", _fake_mount)
    monkeypatch.setattr(api.c2s, "mount_routers", _fake_mount)
    app = object()
    await api.mount_endpoints(app, {})
    assert mounted == [app, app]


async def test_mount_endpoints_respects_deactivate(monkeypatch):
    mounted = []

    monkeypatch.setattr(api.s2s,
                        "mount_routers",
                        lambda app, deactivate: mounted.append("s2s"))
    monkeypatch.setattr(api.c2s,
                        "mount_routers",
                        lambda app, deactivate: mounted.append("c2s"))
    await api.mount_endpoints(object(), {"deactivate_routers": "s2s"})
    assert mounted == ["c2s"]
