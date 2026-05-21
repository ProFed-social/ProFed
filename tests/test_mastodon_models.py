# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import (Account,
                                    Relationship,
                                    MediaAttachment,
                                    MediaAttachmentMeta,
                                    MediaAttachmentMetadata)


def test_account_minimal():
    a = Account(id="1",
                username="alice",
                acct="alice@example.com",
                display_name="Alice",
                url="https://example.com/actors/alice")
    assert a.locked          is False
    assert a.bot             is False
    assert a.followers_count == 0
    assert a.emojis          == []
    assert a.fields          == []
    assert a.source          is None


def test_account_with_source():
    a = Account(id="1",
                username="alice",
                acct="alice@example.com",
                display_name="Alice",
                url="https://example.com/actors/alice",
                source={"privacy": "public",
                        "sensitive": False,
                        "language": None,
                        "note": "",
                        "fields": []})
    assert a.source["privacy"] == "public"


def test_account_with_avatar():
    a = Account(id="1",
                username="alice",
                acct="alice@example.com",
                display_name="Alice",
                url="https://example.com/actors/alice",
                avatar="https://example.com/avatar.png",
                header="https://example.com/header.png")
    assert a.avatar == "https://example.com/avatar.png"
    assert a.header == "https://example.com/header.png"


def test_relationship_defaults():
    r = Relationship(id="123")
    assert r.following       is False
    assert r.requested       is False
    assert r.followed_by     is False
    assert r.blocking        is False
    assert r.note            == ""


def test_relationship_following():
    r = Relationship(id="123", following=True)
    assert r.following is True
    assert r.requested is False


def test_media_attachment_minimal():
    m = MediaAttachment(id="abc", url="https://example.com/media/ab/abc")

    assert m.type == "image"
    assert m.preview_url is None


def test_media_attachment_with_meta():
    m = MediaAttachment(id="abc",
                        url="https://example.com/media/ab/abc",
                        meta=MediaAttachmentMetadata(
                            original=MediaAttachmentMeta(width=1280, height=720),
                            small=MediaAttachmentMeta(width=400, height=225)))

    assert m.meta.original.width == 1280
    assert m.meta.small.height   == 225

