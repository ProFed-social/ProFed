# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from pathlib import Path

from profed.components.client.media import ASSUMED_WIDTH, DOCUMENT_RATIO, MAX_HEIGHT, media_rows


STYLE_CSS = Path(__file__).parents[3] / "src/profed/components/client/static/style.css"
NARROW = 640


def _image(name, width=800, height=600):
    return {"type": "image",
            "url": f"https://r/{name}",
            "meta": {"original": {"width": width, "height": height}}}


def _video(name, width=1920, height=1080):
    return {"type": "video",
            "url": f"https://r/{name}",
            "meta": {"original": {"width": width, "height": height}}}


def _audio(name):
    return {"type": "audio", "url": f"https://r/{name}", "meta": {}}


def _pdf(name, width=None, height=None):
    return {"type": "unknown",
            "mime_type": "application/pdf",
            "url": f"https://r/{name}",
            "meta": {"original": {"width": width, "height": height}} if width else {}}


def _rows(grid):
    return [unit for unit in grid["units"] if unit["kind"] == "row"]


def _names(grid):
    return [[item["item"]["url"].rsplit("/", 1)[1] for item in row["items"]] for row in _rows(grid)]


def _order(grid):
    return [unit["kind"] if unit["kind"] == "row" else unit["flavour"] for unit in grid["units"]]


def _height(row, width):
    return width / sum(item["ratio"] for item in row["items"]) if row["fills"] else MAX_HEIGHT


def test_a_post_without_attachments_has_nothing_to_show():
    grid = media_rows([])

    assert grid["units"] == []
    assert grid["segments"] == []
    assert grid["total"] == 0
    assert grid["extra"] == 0


def test_an_image_carries_its_aspect_ratio():
    grid = media_rows([_image("a", 1920, 1080)])

    assert _rows(grid)[0]["items"][0]["ratio"] == 1920 / 1080


def test_images_share_a_row_until_it_is_full():
    grid = media_rows([_image("a", 1920, 1080), _image("b", 1920, 1080)], assumed_width=NARROW)

    assert _names(grid) == [["a"], ["b"]]


def test_narrow_images_fit_together_in_one_row():
    images = [_image(name, 600, 800) for name in "abc"]

    assert _names(media_rows(images, assumed_width=NARROW)) == [["a", "b", "c"]]


def test_a_row_that_is_full_never_grows_beyond_the_maximum_height():
    grid = media_rows([_image(name, 600, 800) for name in "abcdef"], assumed_width=NARROW)

    assert all(_height(row, NARROW) <= MAX_HEIGHT for row in _rows(grid))


def test_a_trailing_row_is_marked_as_not_filling():
    grid = media_rows([_image("a", 1920, 1080), _image("b", 1000, 1000)], assumed_width=NARROW)

    assert [row["fills"] for row in _rows(grid)] == [True, False]


def test_a_trailing_row_keeps_the_maximum_height():
    grid = media_rows([_image("a", 1000, 1000)], assumed_width=NARROW)

    assert _height(_rows(grid)[0], NARROW) == MAX_HEIGHT


def test_rows_beyond_the_limit_are_counted_instead_of_shown():
    grid = media_rows([_image(name, 1920, 1080) for name in "abcde"], assumed_width=NARROW)

    assert _names(grid) == [["a"], ["b"], ["c"]]
    assert grid["extra"] == 2


def test_the_total_is_reported_whatever_the_row_limit_leaves_out():
    grid = media_rows([_image(name, 1920, 1080) for name in "abcde"], assumed_width=NARROW)

    assert grid["total"] == 5


def test_without_a_row_limit_everything_is_shown():

    grid = media_rows([_image(name, 1920, 1080) for name in "abcde"], max_rows=None, assumed_width=NARROW)

    assert len(_rows(grid)) == 5
    assert grid["extra"] == 0


def test_an_image_without_known_dimensions_becomes_a_block_instead_of_vanishing():
    grid = media_rows([{"type": "image", "url": "https://r/x", "meta": {}}, _image("a")])

    assert _order(grid) == ["image", "row"]
    assert grid["total"] == 2
    assert grid["extra"] == 0


def test_a_video_shares_the_grid_with_the_images():
    grid = media_rows([_image("a", 1600, 900), _video("v"), _image("b", 1600, 900)], assumed_width=3000)

    assert _names(grid) == [["a", "v", "b"]]


def test_an_audio_attachment_interrupts_the_grid_and_keeps_the_authors_order():
    grid = media_rows([_image("a"), _audio("s"), _image("b")], assumed_width=3000)

    assert _order(grid) == ["row", "audio", "row"]


def test_an_audio_attachment_in_front_stays_in_front():
    grid = media_rows([_audio("s"), _image("a"), _image("b")], assumed_width=3000)

    assert _order(grid) == ["audio", "row"]


def test_a_document_is_tiled_as_a_square_whatever_its_pages_measure():
    grid = media_rows([_pdf("d", 794, 1123)])

    assert _rows(grid)[0]["items"][0]["ratio"] == DOCUMENT_RATIO
    assert DOCUMENT_RATIO == 1.0


def test_a_document_without_a_page_size_is_tiled_just_the_same():
    grid = media_rows([_pdf("d")])

    assert _rows(grid)[0]["items"][0]["ratio"] == DOCUMENT_RATIO
    assert _rows(grid)[0]["items"][0]["flavour"] == "document"


def test_a_video_without_dimensions_becomes_a_block():
    grid = media_rows([{"type": "video", "url": "https://r/v", "meta": {}}])

    assert _order(grid) == ["video"]


def test_an_attachment_we_cannot_place_becomes_a_plain_file_block():
    grid = media_rows([{"type": "unknown",
                        "mime_type": "application/zip",
                        "url": "https://r/z",
                        "meta": {"original": {"width": 100, "height": 100}}}])

    assert _order(grid) == ["file"]


def test_neighbouring_rows_become_one_grid_segment():
    grid = media_rows([_image(name, 1920, 1080) for name in "abc"], assumed_width=NARROW)

    assert [segment["kind"] for segment in grid["segments"]] == ["grid"]
    assert len(grid["segments"][0]["rows"]) == 3


def test_a_block_splits_the_grid_into_two_segments():
    grid = media_rows([_image("a"), _audio("s"), _image("b")], assumed_width=3000)

    assert [segment["kind"] for segment in grid["segments"]] == ["grid", "block", "grid"]


def test_a_block_counts_against_the_row_budget():
    grid = media_rows([_audio("s"), _audio("t"), _image("a"), _image("b")], max_rows=2, assumed_width=3000)

    assert _order(grid) == ["audio", "audio"]
    assert grid["extra"] == 2


def test_a_narrower_column_breaks_rows_earlier():
    images = [_image(name, 800, 600) for name in "abcd"]

    assert len(_rows(media_rows(images, assumed_width=320))) > len(_rows(media_rows(images, assumed_width=1280)))


def test_a_row_never_breaks_itself_because_we_decide_where_rows_end():
    css = STYLE_CSS.read_text(encoding="utf-8")
    row = re.search(r"^\.media-row\s*\{([^}]*)\}", css, re.MULTILINE)[1]

    assert "flex-wrap: nowrap" in row


def test_the_maximum_height_is_the_one_the_client_lays_out_with():
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert MAX_HEIGHT == int(re.search(r"--media-max-height:\s*(\d+)px", css)[1])


def test_the_assumed_width_is_as_wide_as_the_layout_column_can_get():
    css = STYLE_CSS.read_text(encoding="utf-8")
    column = int(re.search(r"--col:\s*(\d+)px", css)[1])
    padding = float(re.search(r"^\.column\s*\{[^}]*?padding-inline:\s*([\d.]+)rem", css, re.MULTILINE)[1])

    assert ASSUMED_WIDTH == column - 2 * padding * 16

