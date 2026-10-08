# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from itertools import accumulate, groupby, islice
from operator import itemgetter
from typing import Optional

ASSUMED_WIDTH = 1460
MAX_HEIGHT = 384


def media_rows(attachments,
               max_rows: Optional[int] = 3,
               assumed_width: int = ASSUMED_WIDTH,
               max_height: int = MAX_HEIGHT) -> dict:
    fill = assumed_width / max_height

    def field(item, name):
        return item.get(name) if isinstance(item, dict) else getattr(item, name, None)

    def ratio(item):
        size = (field(item, "meta") or {}).get("original") or {}
        return size["width"] / size["height"] if size.get("width") and size.get("height") else None

    def row_numbers(ratios):
        def placed(so_far, next_ratio):
            row, width = so_far
            return (row + 1, next_ratio) if width >= fill else (row, width + next_ratio)

        return (row for row, _ in islice(accumulate(ratios, placed, initial=(0, 0.0)), 1, None))

    def row_of(images):
        return {"items": images,
                "fills": sum(image["ratio"] for image in images) >= fill}

    images = [image
              for image in ({"item": item, "ratio": ratio(item)}
                            for item in (attachments or [])
                            if field(item, "type") == "image")
              if image["ratio"]]
    rows = [row_of([image for _, image in group])
            for _, group in groupby(zip(row_numbers(image["ratio"] for image in images), images),
                                    key=itemgetter(0))]
    shown = rows if max_rows is None else rows[:max_rows]

    return {"rows": shown,
            "total": len(images),
            "extra": len(images) - sum(len(row["items"]) for row in shown)}

