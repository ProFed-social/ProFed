# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from profed.models import MediaKind
from profed.models.mastodon import media_attachments_from_attachment


@pytest.mark.parametrize("content_type, kind", [("image/jpeg", MediaKind.image),
                                                ("video/mp4", MediaKind.video),
                                                ("audio/mpeg", MediaKind.audio),
                                                ("application/pdf", MediaKind.document)])
def test_a_content_type_names_its_kind(content_type, kind):
    assert MediaKind.of(content_type) is kind


@pytest.mark.parametrize("content_type", ["application/ogg", "audio/x-m4a"])
def test_the_names_browsers_really_send_for_audio_are_understood(content_type):
    assert MediaKind.of(content_type) is MediaKind.audio


def test_a_family_we_do_not_handle_names_no_kind():
    assert MediaKind.of("application/zip") is None
    assert MediaKind.of("") is None
    assert MediaKind.of(None) is None


def _entry(**extra):
    return {"type": "Image", "mediaType": "image/jpeg", "url": "https://remote.example/media/x", **extra}


def test_a_preview_becomes_the_thumbnail():
    entry = _entry(preview={"type": "Image", "url": "https://remote.example/media/x_preview"})

    assert media_attachments_from_attachment([entry])[0]["preview_url"] \
        == "https://remote.example/media/x_preview"


def test_the_preview_wins_over_the_icon():
    entry = _entry(preview={"type": "Image", "url": "https://remote.example/p"},
                   icon={"type": "Image", "url": "https://remote.example/i"})

    assert media_attachments_from_attachment([entry])[0]["preview_url"] == "https://remote.example/p"


def test_without_a_preview_the_icon_is_taken():
    entry = _entry(icon={"type": "Image", "url": "https://remote.example/i"})

    assert media_attachments_from_attachment([entry])[0]["preview_url"] == "https://remote.example/i"


def test_an_icon_given_as_a_bare_url_is_understood():
    assert media_attachments_from_attachment([_entry(icon="https://remote.example/i")])[0]["preview_url"] \
        == "https://remote.example/i"


def test_an_image_without_either_falls_back_to_the_original():
    assert media_attachments_from_attachment([_entry()])[0]["preview_url"] \
        == "https://remote.example/media/x"


def test_audio_without_either_gets_no_thumbnail():
    entry = {"type": "Audio", "mediaType": "audio/mpeg", "url": "https://remote.example/media/a"}

    assert media_attachments_from_attachment([entry])[0]["preview_url"] is None

