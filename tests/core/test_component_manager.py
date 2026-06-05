# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from types import ModuleType
from pytest import fixture, mark, raises

from profed.core.component_manager import run, Component, collect_component_hooks, ComponentError

@fixture
def mock_module():
    mod = ModuleType("profed.components.example")
    sys.modules["profed.components.example"] = mod
    exec("async def Example(cfg):\n"
         "    assert(cfg[\"foo\"] == \"bar\")\n",
         mod.__dict__)


def test_component_manager_with_main(mock_module):
    run({"example": {"foo": "bar"}, "profed": {"run": ["example"]}})


def test_component_manager_without_main(mock_module):
    run({"example": {"foo": "bar"}, "profed": {"run": ["example"]}})


@mark.asyncio
async def test_component(mock_module):
    cmp = Component("example")
    await cmp({"foo": "bar"})


@fixture
def fake_components():
    created = []
    def make(name, **attrs):
        full = f"profed.components.{name}"
        mod = ModuleType(full)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules[full] = mod
        created.append(full)
    yield make
    for full in created:
        sys.modules.pop(full, None)


def test_collect_component_hooks_only_components_with_hook(fake_components):
    fake_components("alpha", mount_endpoints=lambda app, cfg: None)
    fake_components("beta")
    fake_components("gamma", mount_endpoints=lambda app, cfg: None)

    hooks = collect_component_hooks(["alpha", "beta", "gamma"], "mount_endpoints")

    assert list(hooks.keys()) == ["alpha", "gamma"]


def test_collect_component_hooks_empty_when_none_offer_it(fake_components):
    fake_components("alpha")
    fake_components("beta")

    assert collect_component_hooks(["alpha", "beta"], "mount_endpoints") == {}


def test_collect_component_hooks_preserves_runlist_order(fake_components):
    fake_components("gamma", mount_endpoints=lambda app, cfg: None)
    fake_components("alpha", mount_endpoints=lambda app, cfg: None)

    hooks = collect_component_hooks(["gamma", "alpha"], "mount_endpoints")

    assert list(hooks.keys()) == ["gamma", "alpha"]


def test_collect_component_hooks_accepts_string(fake_components):
    fake_components("alpha", mount_endpoints=lambda app, cfg: None)
    fake_components("beta", mount_endpoints=lambda app, cfg: None)

    hooks = collect_component_hooks("alpha beta", "mount_endpoints")

    assert list(hooks.keys()) == ["alpha", "beta"]


def test_collect_component_hooks_returns_the_attribute(fake_components):
    def my_hook(app, cfg):
        return None
    fake_components("alpha", mount_endpoints=my_hook)

    hooks = collect_component_hooks(["alpha"], "mount_endpoints")

    assert hooks["alpha"] is my_hook


def test_collect_component_hooks_raises_for_unimportable_component():
    with raises(ComponentError):
        collect_component_hooks(["does_not_exist_xyz"], "mount_endpoints")


