# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List, Optional, Tuple


def _top_of_run(row: dict, by_url: dict) -> dict:
    parent = by_url.get(row["in_reply_to"])
    return _top_of_run(parent, by_url) if parent is not None and not parent["visible"] else row


def _visible_ancestor(row: dict, by_url: dict) -> Optional[dict]:
    parent = by_url.get(row["in_reply_to"])
    return (None
            if parent is None else
            parent
            if parent["visible"] else
            _visible_ancestor(parent, by_url))


def collapse(rows: List[dict]) -> Tuple[List[dict], List[dict]]:
    by_url = {row["url"]: row for row in rows}

    def run_top_of(row):
        return _top_of_run(by_url[row["in_reply_to"]], by_url)

    def hidden_parent(row):
        return row["in_reply_to"] in by_url and not by_url[row["in_reply_to"]]["visible"]

    def shown(row):
        return ({**row, "in_reply_to": run_top_of(row)["url"], "attach_to": run_top_of(row)["mastodon_id"]}
                if hidden_parent(row) else
                {**row, "attach_to": None})

    def placeholder_of(top):
        above = _visible_ancestor(top, by_url)
        return {"mastodon_id": top["mastodon_id"],
                "url": top["url"],
                "in_reply_to": above["url"] if above is not None else None}

    tops = {run_top_of(row)["url"]: run_top_of(row) for row in rows if row["visible"] and hidden_parent(row)}

    return [shown(row) for row in rows if row["visible"]], [placeholder_of(top) for top in tops.values()]

