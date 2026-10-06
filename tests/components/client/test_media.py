# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.client.media import media_rows


def _image(name):
    return {"type": "image", "url": f"https://r/{name}"}


def _urls(rows):
    return ([rows["lead"]["url"]] if rows["lead"] else []) + [item["url"] for pair in rows["pairs"] for item in pair]


def test_a_post_without_attachments_has_nothing_to_show():
    rows = media_rows([])

    assert rows["lead"] is None
    assert rows["pairs"] == []
    assert rows["extra"] == 0


def test_a_single_image_leads_on_its_own_row():
    rows = media_rows([_image("a")])

    assert rows["lead"]["url"] == "https://r/a"
    assert rows["pairs"] == []


def test_two_images_share_one_row():
    rows = media_rows([_image("a"), _image("b")])

    assert rows["lead"] is None
    assert [item["url"] for item in rows["pairs"][0]] == ["https://r/a", "https://r/b"]


def test_three_images_put_the_first_on_top_and_the_rest_below():
    rows = media_rows([_image("a"), _image("b"), _image("c")])

    assert rows["lead"]["url"] == "https://r/a"
    assert [item["url"] for item in rows["pairs"][0]] == ["https://r/b", "https://r/c"]


def test_four_images_make_two_full_rows():
    rows = media_rows([_image(name) for name in "abcd"])

    assert rows["lead"] is None
    assert len(rows["pairs"]) == 2


def test_six_images_fill_the_three_rows_a_timeline_allows():
    rows = media_rows([_image(name) for name in "abcdef"])

    assert len(rows["pairs"]) == 3
    assert rows["extra"] == 0

def test_five_images_fill_three_rows_with_one_on_top():
    rows = media_rows([_image(name) for name in "abcde"])

    assert rows["lead"]["url"] == "https://r/a"
    assert len(rows["pairs"]) == 2
    assert rows["extra"] == 0


def test_what_does_not_fit_is_counted_instead_of_shown():
    rows = media_rows([_image(name) for name in "abcdefgh"])

    assert len(_urls(rows)) == 6
    assert rows["extra"] == 2


def test_an_odd_overflowing_set_keeps_its_leading_image():
    rows = media_rows([_image(name) for name in "abcdefg"])

    assert rows["lead"]["url"] == "https://r/a"
    assert len(_urls(rows)) == 5
    assert rows["extra"] == 2


def test_without_a_row_limit_everything_is_shown():
    rows = media_rows([_image(name) for name in "abcdefghij"], max_rows=None)

    assert len(_urls(rows)) == 10
    assert rows["extra"] == 0


def test_anything_that_is_not_an_image_is_left_out_for_now():
    rows = media_rows([{"type": "video", "url": "https://r/v"}, _image("a")])

    assert _urls(rows) == ["https://r/a"]
    assert rows["extra"] == 0

