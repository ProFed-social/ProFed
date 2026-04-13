# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from collections import defaultdict


class FakeConnection:
    def __init__(self, db):
        self._db = db
        self.notifies = []
        self._listeners = {}

    class _Transaction:
        async def start(self):
            return None

        async def commit(self):
            return None

        async def rollback(self):
            return None

    def transaction(self):
        return self._Transaction()

    async def execute(self, query: str, *args):
        if query.startswith("NOTIFY"):
            channel = query.split()[1]
            for conn in self._db.connections:
                for callback in list(conn._listeners.get(channel, [])):
                    callback(conn, 0, channel, "")
        elif "INSERT INTO" in query:
            if "_snapshots" in query:
                self._db.insert_snapshot(self._extract_table(query),
                                         args[0],
                                         args[1])
            elif "_gaps" in query:
                self._db.insert_gap(self._extract_table(query),
                                    args[0])
            else:
                self._db.insert_message(self._extract_table(query),
                                        args[0],
                                        i=args[1])
        elif "DELETE" in query:
            self._db.delete_gaps(self._extract_table(query),
                                 args[0])

    def _fetch_single_table(self, table_name, *args):
        if "_snapshots" in table_name:
            return self._db.fetch_snapshots(self._extract_table(table_name))
        elif "_gaps" in table_name:
            return self._db.fetch_gaps(self._extract_table(table_name))
        else:
            return self._db.fetch_messages(self._extract_table(table_name),
                                           args[0] if len(args) > 0 else 0)

    def join(self, left_rows, right_rows, l_col, r_col):
        return [{**lr, **rr}
                for lr in left_rows
                for rr in right_rows
                if lr[l_col] == rr[r_col]]

    async def fetch(self, query: str, *args):
        if "FROM" in query:
            tables = re.findall(r"FROM\s+([^\s]+)\s+([^\s]+)\s+JOIN\s+([^\s]+)\s+([^\s]+)\s+ON\s+([^\s]+)\.([^\s]+)\s*=\s*([^\s]+)\.([^\s]+)",
                                query.upper(),
                                re.IGNORECASE)
            if not tables:
                return self._fetch_single_table(self._extract_table(query), *args)

            left_table, _, right_table, _, _, l_col, _, r_col = tables[0]

            return self.join(self._fetch_single_table(left_table.lower(), *args),
                             self._fetch_single_table(right_table.lower(), *args),
                             l_col.lower(),
                             r_col.lower())
        elif "INSERT INTO" in query:
            return self._db.insert_message(self._extract_table(query), *args)

        return []

    async def fetchrow(self, query: str, *args):
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def add_listener(self, channel: str, callback) -> None:
        self._listeners.setdefault(channel, []).append(callback)
 
    async def remove_listener(self, channel: str, callback) -> None:
        if channel in self._listeners:
            try:
                self._listeners[channel].remove(callback)
            except ValueError:
                pass
 
    def _extract_table(self, query: str) -> str:
        for part in query.split():
            if "." in part:
                return part.strip()
        raise RuntimeError("Cannot parse table name")


class FakePool:
    def __init__(self, db):
        self._db = db

    def acquire(self):
        conn = FakeConnection(self._db)
        self._db.connections.append(conn)
        return _FakeAcquireContext(conn)


class _FakeAcquireContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class InMemoryDatabase:
    def __init__(self):
        self.messages = defaultdict(list)
        self.snapshots = defaultdict(list)
        self.gaps = defaultdict(set)
        self.connections = []

    def insert_message(self, table, payload, message_id = None, i = None):
        table_messages = self.messages[table]
        new_id = i if i is not None else len(table_messages) + 1
        if message_id is None or message_id not in (m["message_id"] for m in table_messages):
            table_messages.append({"id": new_id, "payload": payload, "message_id": message_id})
            return [{"id": new_id}]
        return None

    def fetch_messages(self, table, last_seen):
        return sorted((m
                       for m in self.messages[table]
                       if m["id"] > last_seen),
                      key=lambda m: m["id"])

    def insert_snapshot(self, table, payload, event_id):
        self.snapshots[table].append({"payload": payload,
                                      "last_event_id": event_id})

    def fetch_snapshots(self, table):
        sorted_snaps = sorted(self.snapshots[table],
                              key=lambda s: s["last_event_id"],
                              reverse=True)
        return ([{"last_event_id": sorted_snaps[1]["last_event_id"]}]
                if len(sorted_snaps) >= 2 else
                [])

    def insert_gap(self, table, missing_id):
        self.gaps[table].add(missing_id)

    def fetch_gaps(self, table):
        return [{"missing_id": i} for i in self.gaps[table]]

    def delete_gaps(self, table, row_id):
        self.gaps[table] = {row
                            for row in self.gaps[table]
                            if row >= row_id}
