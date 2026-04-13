# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.components.api.config import parse


def test_database_credentials_are_merged():
    db = {"host": "localhost", "port": "5432",
          "database": "mydb", "user": "u", "password": "p"}
    result = parse({}, db)
    assert result["host"] == "localhost"
    assert result["database"] == "mydb"


def test_listen_defaults_are_applied():
    result = parse({}, {})
    assert result["listen_host"] == "127.0.0.1"
    assert result["listen_port"] == "8000"


def test_explicit_listen_values_are_preserved():
    result = parse({"listen_host": "0.0.0.0", "listen_port": "9000"}, {})
    assert result["listen_host"] == "0.0.0.0"
    assert result["listen_port"] == "9000"


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

