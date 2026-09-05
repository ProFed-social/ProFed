# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.config import parse


def test_database_credentials_are_merged():
    db = {"host": "localhost", "port": "5432",
          "database": "mydb", "user": "u", "password": "p"}
    result = parse({}, db)
    assert result["host"] == "localhost"
    assert result["database"] == "mydb"


def test_host_and_port_remain_available_for_db():
    db = {"host": "localhost", "port": "5432",
          "database": "mydb", "user": "u", "password": "p"}
    result = parse({}, db)
    assert result["host"] == "localhost"
    assert result["port"] == "5432"


def test_component_db_overrides_database_section():
    cfg = {"host": "other-db.example.com", "database": "other"}
    db  = {"host": "localhost",
           "port": "5432",
           "database": "mydb",
           "user": "u",
           "password": "p"}
    result = parse(cfg, db)
    assert result["host"] == "other-db.example.com"
    assert result["database"] == "other"
    assert result["user"] == "u"


def test_background_task_tuning_gets_numeric_defaults():
    result = parse({}, {})

    assert result["sweeping_sleep_min"] == 60.0
    assert result["sweeping_sleep_max"] == 3600.0
    assert result["sweeping_agility"] == 500.0
    assert result["compression_sample_size"] == 100
    assert result["compression_sleep_min"] == 1.0
    assert result["compression_sleep_max"] == 60.0
    assert result["compression_agility"] == 50.0


def test_background_task_tuning_converts_configured_values():
    result = parse({"sweeping_sleep_min": "5", "compression_sample_size": "7"}, {})

    assert result["sweeping_sleep_min"] == 5.0
    assert result["compression_sample_size"] == 7

