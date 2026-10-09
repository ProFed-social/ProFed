# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from pathlib import Path

from profed.components.client.media import ASSUMED_WIDTH, MAX_HEIGHT, media_rows


STYLE_CSS = Path(__file__).parents[3] / "src/profed/components/client/static/style.css"
NARROW = 640


def _image(name, width=800, height=600):
    return {"type": "image",
            "url": f"https://r/{name}",
            "meta": {"original": {"width": width, "height": height}}}


def _names(rows):
    return [[item["item"]["url"].rsplit("/", 1)[1] for item in row["items"]] for row in rows["rows"]]


def _height(row, width):
    return width / sum(item["ratio"] for item in row["items"]) if row["fills"] else MAX_HEIGHT


def test_a_post_without_attachments_has_no_rows():
    rows = media_rows([])

    assert rows["rows"] == []
    assert rows["total"] == 0
    assert rows["extra"] == 0


def test_an_image_carries_its_aspect_ratio():
    rows = media_rows([_image("a", 1920, 1080)])

    assert rows["rows"][0]["items"][0]["ratio"] == 1920 / 1080


def test_images_share_a_row_until_it_is_full():
    rows = media_rows([_image("a", 1920, 1080), _image("b", 1920, 1080)], assumed_width=NARROW)

    assert _names(rows) == [["a"], ["b"]]


def test_narrow_images_fit_together_in_one_row():
    images = [_image(name, 600, 800) for name in "abc"]

    assert _names(media_rows(images, assumed_width=NARROW)) == [["a", "b", "c"]]


def test_a_row_that_is_full_never_grows_beyond_the_maximum_height():
    rows = media_rows([_image(name, 600, 800) for name in "abcdef"], assumed_width=NARROW)

    assert all(_height(row, NARROW) <= MAX_HEIGHT for row in rows["rows"])


def test_a_trailing_row_is_marked_as_not_filling():
    rows = media_rows([_image("a", 1920, 1080), _image("b", 1000, 1000)], assumed_width=NARROW)

    assert [row["fills"] for row in rows["rows"]] == [True, False]


def test_a_trailing_row_keeps_the_maximum_height():
    rows = media_rows([_image("a", 1000, 1000)], assumed_width=NARROW)

    assert _height(rows["rows"][0], NARROW) == MAX_HEIGHT


def test_rows_beyond_the_limit_are_counted_instead_of_shown():
    rows = media_rows([_image(name, 1920, 1080) for name in "abcde"], assumed_width=NARROW)

    assert _names(rows) == [["a"], ["b"], ["c"]]
    assert rows["extra"] == 2


def test_the_total_is_reported_whatever_the_row_limit_leaves_out():
    rows = media_rows([_image(name, 1920, 1080) for name in "abcde"], assumed_width=NARROW)

    assert rows["total"] == 5


def test_without_a_row_limit_everything_is_shown():
    rows = media_rows([_image(name, 1920, 1080) for name in "abcde"], max_rows=None, assumed_width=NARROW)

    assert len(rows["rows"]) == 5
    assert rows["extra"] == 0


def test_an_image_without_known_dimensions_is_left_out():
    rows = media_rows([{"type": "image", "url": "https://r/x", "meta": {}}, _image("a")])

    assert _names(rows) == [["a"]]
    assert rows["total"] == 1
    assert rows["extra"] == 0


def test_anything_that_is_not_an_image_is_left_out_for_now():
    rows = media_rows([{"type": "video", "url": "https://r/v", "meta": {"original": {"width": 800, "height": 600}}},
                       _image("a")])

    assert _names(rows) == [["a"]]


def test_a_narrower_column_breaks_rows_earlier():
    images = [_image(name, 800, 600) for name in "abcd"]

    assert len(media_rows(images, assumed_width=320)["rows"]) > len(media_rows(images, assumed_width=1280)["rows"])


def test_the_maximum_height_is_the_one_the_client_lays_out_with():
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert MAX_HEIGHT == int(re.search(r"--media-max-height:\s*(\d+)px", css)[1])


def test_the_assumed_width_is_as_wide_as_the_layout_column_can_get():
    css = STYLE_CSS.read_text(encoding="utf-8")
    column = int(re.search(r"--col:\s*(\d+)px", css)[1])
    padding = float(re.search(r"^\.column\s*\{[^}]*?padding-inline:\s*([\d.]+)rem", css, re.MULTILINE)[1])

    assert ASSUMED_WIDTH == column - 2 * padding * 16

