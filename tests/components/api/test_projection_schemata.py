# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pathlib


API = pathlib.Path(__file__).resolve().parents[3] / "src" / "profed" / "components" / "api"


def _projection_modules():
    return [path for path in API.rglob("*projection*.py")
            if "init as init_storage" in path.read_text()]


def test_every_projection_that_owns_a_storage_creates_its_schema():
    without = [str(path.relative_to(API))
               for path in _projection_modules()
               if "ensure_schema" not in path.read_text()
               and "build_person_projection" not in path.read_text()]

    assert without == []


def test_every_projection_that_creates_a_schema_also_hands_it_to_the_builder():
    unwired = [str(path.relative_to(API))
               for path in _projection_modules()
               if "async def _init()" in path.read_text() and "init=_init" not in path.read_text()]

    assert unwired == []


def test_the_search_finds_the_projections_it_is_meant_to_check():
    assert len(_projection_modules()) > 15

