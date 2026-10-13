# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from profed.models import MediaKind


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

