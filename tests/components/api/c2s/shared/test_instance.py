# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from profed.core.config import config, raw
from profed.components.api.c2s.shared.instance import build_common_response
from profed.languages import supported
from profed.models import MediaKind
from profed.components.api.c2s.shared.media.upload import max_media_attachments, size_limit, supported_types


class Cfg:
    def __init__(self, cfg):
        raw.paths = []
        raw.argv = [""] + [f"--{s}.{k}={v}"
                            for s, d in cfg.items()
                            for k, v in d.items()]
        os.environ = {k: v for k, v in os.environ.items()
                      if not k.startswith("PROFED_")}

    def __enter__(self):
        config.reset()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val


def test_build_common_response_contains_title():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({"title": "My ProFed"}, "example.com", 5000)
    assert result["title"] == "My ProFed"


def test_build_common_response_max_characters():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 3000)
    assert result["configuration"]["statuses"]["max_characters"] == 3000


def test_build_common_response_default_title_is_domain():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)
    assert result["title"] == "example.com"


def test_build_common_response_languages_is_the_supported_set():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)
    assert result["languages"] == sorted(supported())
    assert "en" in result["languages"]


def test_the_instance_reports_the_media_types_it_actually_accepts():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)

    assert set(result["configuration"]["media_attachments"]["supported_mime_types"]) == supported_types()


def test_the_instance_reports_the_size_limit_it_actually_enforces():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)

    assert result["configuration"]["media_attachments"]["image_size_limit"] == size_limit(MediaKind.image)


def test_the_instance_reports_how_many_attachments_a_status_may_carry():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)

    assert result["configuration"]["statuses"]["max_media_attachments"] == max_media_attachments()


def test_the_instance_reports_a_configured_attachment_limit():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com", "max_media_attachments": "4"}}):
        result = build_common_response({}, "example.com", 5000)

    assert result["configuration"]["statuses"]["max_media_attachments"] == 4


def test_the_instance_reports_a_configured_video_size_limit():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com", "video_size_limit": "12345"}}):
        result = build_common_response({}, "example.com", 5000)

    assert result["configuration"]["media_attachments"]["video_size_limit"] == 12345


def test_the_instance_reports_the_audio_and_document_limits_as_an_extension():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)

    extension = result["configuration"]["media_attachments"]["profed"]
    assert extension["audio_size_limit"] == size_limit(MediaKind.audio)
    assert extension["document_size_limit"] == size_limit(MediaKind.document)


def test_the_instance_accepts_video_audio_and_documents():
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        result = build_common_response({}, "example.com", 5000)

    offered = set(result["configuration"]["media_attachments"]["supported_mime_types"])
    assert {"video/mp4", "audio/mpeg", "application/pdf"} <= offered

