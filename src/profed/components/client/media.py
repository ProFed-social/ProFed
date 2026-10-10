# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from itertools import accumulate, groupby, islice
from operator import itemgetter
from typing import Optional

ASSUMED_WIDTH = 1460
MAX_HEIGHT = 384
DOCUMENT_RATIO = 1.0
TILED = {"image", "video", "document"}


def media_rows(attachments,
               max_rows: Optional[int] = 3,
               assumed_width: int = ASSUMED_WIDTH,
               max_height: int = MAX_HEIGHT) -> dict:
    def classified(attachments) -> list[dict]:
        def entry(item):
            def field(item, name):
                return item.get(name) if isinstance(item, dict) else getattr(item, name, None)

            def flavour(item) -> str:
                kind = field(item, "type")

                return ("image"
                        if kind in ("image", "gifv") else
                        "video"
                        if kind == "video" else
                        "audio"
                        if kind == "audio" else
                        "document"
                        if (field(item, "mime_type") or "") == "application/pdf" else
                        "file")
            flav = flavour(item)

            def ratio(item, flavour: str) -> Optional[float]:
                if flavour == "document":
                    return DOCUMENT_RATIO

                size = (field(item, "meta") or {}).get("original") or {}

                return size["width"] / size["height"] if size.get("width") and size.get("height") else None

            rt = ratio(item, flav) if flav in TILED else None

            return ({"kind": "tile", "item": item, "flavour": flav, "ratio": rt}
                    if rt else
                    {"kind": "block", "item": item, "flavour": flav})

        return [entry(item) for item in (attachments or [])]

    clsified = classified(attachments)

    def _rows_of(tiles: list[dict], fill: float) -> list[dict]:
        def row_numbers(ratios):
            def placed(so_far, next_ratio):
                row, width = so_far
                return (row + 1, next_ratio) if width >= fill else (row, width + next_ratio)

            return (row for row, _ in islice(accumulate(ratios, placed, initial=(0, 0.0)), 1, None))

        def row_of(items):
            return {"kind": "row",
                    "items": items,
                    "fills": sum(item["ratio"] for item in items) >= fill}

        return [row_of([tile for _, tile in group])
                for _, group in groupby(zip(row_numbers(tile["ratio"] for tile in tiles), tiles),
                                        key=itemgetter(0))]

    def segments(classified: list[dict], fill: float) -> list[dict]:
        return [unit
                for is_tile, group in groupby(classified, key=lambda entry: entry["kind"] == "tile")
                for unit in (_rows_of(list(group), fill) if is_tile else list(group))]

    units = segments(clsified, assumed_width / max_height)
    shown = units if max_rows is None else units[:max_rows]

    def counted(unit: dict) -> int:
        return len(unit["items"]) if unit["kind"] == "row" else 1

    def grouped(units: list[dict]) -> list[dict]:
        return [segment
                for is_row, group in groupby(units, key=lambda unit: unit["kind"] == "row")
                for segment in ([{"kind": "grid", "rows": list(group)}] if is_row else list(group))]

    return {"segments": grouped(shown),
            "units": shown,
            "total": len(clsified),
            "extra": len(clsified) - sum(counted(unit) for unit in shown)}

