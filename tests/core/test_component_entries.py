# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pathlib
import pytest


COMPONENTS = pathlib.Path(__file__).resolve().parents[2] / "src" / "profed" / "components"


def _component_files():
    return sorted(path.parent.name for path in COMPONENTS.glob("*/storage.py"))


@pytest.mark.parametrize("component", _component_files())
def test_a_component_with_a_storage_reports_its_rebuild(component):
    sources = [path.read_text() for path in (COMPONENTS / component).glob("*.py")]

    assert any("rebuild_finished" in source for source in sources), \
        f"{component} never calls rebuild_finished, so every storage call would block forever"


@pytest.mark.parametrize("component", _component_files())
def test_a_component_with_a_storage_creates_its_schema(component):
    sources = [path.read_text() for path in (COMPONENTS / component).glob("*.py")]

    assert any("ensure_schema" in source for source in sources), \
        f"{component} never calls ensure_schema"

