# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.config.database import with_database_defaults


def test_missing_db_fields_are_filled():
    db = {"host": "localhost",
          "port": "5432",
          "database": "mydb",
          "user": "myuser",
          "password": "secret"}
    result = with_database_defaults({}, db)
    assert result["host"] == "localhost"
    assert result["database"] == "mydb"
    assert result["password"] == "secret"


def test_existing_fields_are_not_overridden():
    component = {"host": "db.example.com", "database": "other"}
    db = {"host": "localhost", "database": "mydb", "user": "u", "password": "p"}
    result = with_database_defaults(component, db)
    assert result["host"] == "db.example.com"
    assert result["database"] == "other"
    assert result["user"] == "u"


def test_only_db_keys_are_merged():
    db = {"host": "localhost",
          "port": "5432",
          "database": "mydb",
          "user": "u",
          "password": "p",
          "schema": "public"}
    result = with_database_defaults({}, db)
    assert "schema" not in result


def test_original_dicts_are_not_mutated():
    component = {"listen_host": "127.0.0.1"}
    db = {"host": "localhost",
          "port": "5432",
          "database": "d",
          "user": "u",
          "password": "p"}
    _ = with_database_defaults(component, db)
    assert "host" not in component


def test_empty_database_cfg_is_harmless():
    component = {"host": "myhost", "custom": "value"}
    result = with_database_defaults(component, {})
    assert result == component

