# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone

from profed.identity import account_id
from profed.models.mastodon import (Account,
                                    Status,
                                    mentions_from_tag,
                                    tags_from_tag,
                                    media_attachments_from_attachment,
                                    Relationship,
                                    MediaAttachment,
                                    MediaAttachmentMeta,
                                    MediaAttachmentMetadata,
                                    placeholder_account)


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


def test_from_actor_maps_fields():
    acc = Account.from_actor({"type":    "Person",
                              "name":    "Bob Example",
                              "summary": "A test user",
                              "icon":    {"url": "https://remote.example/avatar.png"},
                              "image":   {"url": "https://remote.example/header.png"}},
                             acct="bob@remote.example",
                             url="https://remote.example/actors/bob")

    assert acc.id            == account_id("bob@remote.example")
    assert acc.username      == "bob"
    assert acc.acct          == "bob@remote.example"
    assert acc.display_name  == "Bob Example"
    assert acc.note          == "A test user"
    assert acc.url           == "https://remote.example/actors/bob"
    assert acc.avatar        == "https://remote.example/avatar.png"
    assert acc.avatar_static == "https://remote.example/avatar.png"
    assert acc.header        == "https://remote.example/header.png"
    assert acc.locked        is False
    assert acc.bot           is False


def test_from_actor_falls_back_to_username():
    acc = Account.from_actor({"type": "Person"},
                             acct="carol@other.example",
                             url="https://other.example/actors/carol")

    assert acc.display_name == "carol"
    assert acc.avatar       is None
    assert acc.header       is None


def test_from_actor_handles_missing_actor():
    acc = Account.from_actor({},
                             acct="carol@other.example",
                             url="https://other.example/actors/carol")

    assert acc.display_name == "carol"
    assert acc.bot          is False


def test_from_actor_sets_bot_for_service():
    acc = Account.from_actor({"type": "Service"},
                             acct="bot@example.com",
                             url="https://example.com/actors/bot")

    assert acc.bot is True


def test_from_actor_sets_locked_from_manually_approves():
    acc = Account.from_actor({"type": "Person", "manuallyApprovesFollowers": True},
                             acct="x@example.com",
                             url="https://example.com/actors/x")

    assert acc.locked is True


def test_from_actor_sets_created_at_from_datetime():
    created = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    acc = Account.from_actor({"type": "Person"},
                             acct="x@example.com",
                             url="https://example.com/actors/x",
                             created_at=created)

    assert acc.created_at == created.isoformat()


def test_from_actor_uses_published_when_no_created_at():
    acc = Account.from_actor({"type": "Person", "published": "2020-05-05T00:00:00+00:00"},
                             acct="x@example.com",
                             url="https://example.com/actors/x")

    assert acc.created_at == "2020-05-05T00:00:00+00:00"


def test_from_actor_created_at_overrides_published():
    acc = Account.from_actor({"type": "Person", "published": "2020-05-05T00:00:00+00:00"},
                             acct="x@example.com",
                             url="https://example.com/actors/x",
                             created_at="2021-06-06T00:00:00+00:00")

    assert acc.created_at == "2021-06-06T00:00:00+00:00"


def test_from_actor_maps_resume():
    acc = Account.from_actor({"type": "Person", "resume": {"skills": [{"name": "Python"}]}},
                             acct="bob@remote.example",
                             url="https://remote.example/actors/bob")

    assert acc.resume is not None
    assert acc.resume.skills == [{"name": "Python"}]


def test_from_actor_without_resume_is_none():
    acc = Account.from_actor({"type": "Person"},
                             acct="bob@remote.example",
                             url="https://remote.example/actors/bob")

    assert acc.resume is None


def test_from_actor_sanitizes_note_from_summary():
    acc = Account.from_actor({"type":    "Person",
                              "summary": "<p>hi</p><script>alert(1)</script>"},
                             acct="mallory@remote.example",
                             url="https://remote.example/actors/mallory")

    assert acc.note == "<p>hi</p>"


def test_from_actor_preserves_resume():
    acc = Account.from_actor({"type": "Person",
                              "resume": {"skills": [{"name": "Python"}]}},
                             acct="bob@remote.example",
                             url="https://remote.example/actors/bob")

    assert acc.resume.skills == [{"name": "Python"}]


MENTION = {"type": "Mention", "href": "https://r.example/actors/dave", "name": "@dave@r.example"}
HASHTAG = {"type": "Hashtag", "href": "https://x.example/tags/news", "name": "#news"}


def test_mentions_from_tag_builds_mastodon_mention():
    assert mentions_from_tag([MENTION]) == [{"id": account_id("dave@r.example"),
                                             "username": "dave",
                                             "url": "https://r.example/actors/dave",
                                             "acct": "dave@r.example"}]


def test_mentions_from_tag_ignores_hashtags():
    assert mentions_from_tag([HASHTAG]) == []


def test_tags_from_tag_builds_hashtag():
    assert tags_from_tag([HASHTAG]) == [{"name": "news", "url": "https://x.example/tags/news"}]


def test_from_activity_builds_status_with_given_account():
    account = Account(id="7", username="dave", acct="dave@r.example",
                      display_name="Dave", url="https://r.example/actors/dave")
    activity = {"actor": "https://r.example/actors/dave",
                "id": "https://r.example/notes/1#create",
                "object": {"id": "https://r.example/notes/1",
                           "url": "https://r.example/notes/1",
                           "published": "2026-01-01T00:00:00.000Z",
                           "content": "hi @dave@r.example",
                           "tag": [MENTION]}}
    status = Status.from_activity(activity, id="42", account=account)

    assert status.id == "42"
    assert status.account.id == "7"
    assert status.uri == "https://r.example/notes/1#create"
    assert status.url == "https://r.example/notes/1"
    assert status.content == "hi @dave@r.example"
    assert status.mentions == [{"id": account_id("dave@r.example"), "username": "dave",
                                "url": "https://r.example/actors/dave", "acct": "dave@r.example"}]


def test_from_activity_reads_the_url_from_a_link_array():
    activity = {"actor": "https://r.example/actors/dave",
                "id": "https://r.example/notes/1#create",
                "object": {"id": "https://r.example/notes/1",
                           "url": [{"href": "https://r.example/notes/1", "type": "Link"}],
                           "content": "hi"}}

    status = Status.from_activity(activity, id="42")

    assert status.url == "https://r.example/notes/1"


def test_from_activity_uses_placeholder_account_when_missing():
    activity = {"actor": "https://local/actors/alice", "object": {"content": "hi"}}
    status = Status.from_activity(activity, id="42")

    assert status.account.id == "0"
    assert status.account.username == "alice"


def test_from_activity_carries_in_reply_to_as_the_parent_url():
    activity = {"actor": "https://local/actors/alice",
                "object": {"content": "a reply", "inReplyTo": "https://r.example/notes/7"}}
    status = Status.from_activity(activity, id="42")

    assert status.in_reply_to_id == "https://r.example/notes/7"


def test_from_activity_leaves_in_reply_to_none_for_a_top_level_post():
    activity = {"actor": "https://local/actors/alice", "object": {"content": "hi"}}
    status = Status.from_activity(activity, id="42")

    assert status.in_reply_to_id is None


def test_from_activity_account_less_content_dump_excludes_account():
    activity = {"actor": "https://local/actors/alice", "object": {"content": "hi"}}
    dump = Status.from_activity(activity, id="42").model_dump(exclude={"account"})

    assert "account" not in dump
    assert dump["id"] == "42"
    assert dump["content"] == "hi"


def test_media_attachments_keep_the_exact_mime_type():
    assert media_attachments_from_attachment([IMAGE_ATTACHMENT])[0]["mime_type"] == "image/jpeg"


def test_a_missing_media_type_leaves_the_mime_type_empty():
    entry = {"type": "Image", "url": "https://r.example/i.png"}

    assert media_attachments_from_attachment([entry])[0]["mime_type"] is None


IMAGE_ATTACHMENT = {"type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://r.example/media/1.jpg",
                    "name": "Ein Alt-Text",
                    "blurhash": "L6PZ",
                    "width": 1200,
                    "height": 800}


def test_media_attachments_reads_the_url():
    assert media_attachments_from_attachment([IMAGE_ATTACHMENT])[0]["url"] == "https://r.example/media/1.jpg"


def test_media_attachments_carry_the_alt_text_as_description():
    assert media_attachments_from_attachment([IMAGE_ATTACHMENT])[0]["description"] == "Ein Alt-Text"


def test_media_attachments_keep_the_blurhash():
    assert media_attachments_from_attachment([IMAGE_ATTACHMENT])[0]["blurhash"] == "L6PZ"


def test_media_attachments_record_the_dimensions():
    meta = media_attachments_from_attachment([IMAGE_ATTACHMENT])[0]["meta"]

    assert meta["original"] == {"width": 1200, "height": 800}


def test_an_image_media_type_yields_an_image():
    assert media_attachments_from_attachment([IMAGE_ATTACHMENT])[0]["type"] == "image"


def test_a_video_media_type_yields_a_video():
    entry = {"type": "Document", "mediaType": "video/mp4", "url": "https://r.example/v.mp4"}

    assert media_attachments_from_attachment([entry])[0]["type"] == "video"


def test_an_audio_media_type_yields_audio():
    entry = {"type": "Document", "mediaType": "audio/ogg", "url": "https://r.example/a.ogg"}

    assert media_attachments_from_attachment([entry])[0]["type"] == "audio"


def test_the_object_type_types_the_attachment_without_a_media_type():
    entry = {"type": "Image", "url": "https://r.example/i.png"}

    assert media_attachments_from_attachment([entry])[0]["type"] == "image"


def test_an_unknown_kind_is_typed_as_unknown():
    entry = {"url": "https://r.example/x.bin"}

    assert media_attachments_from_attachment([entry])[0]["type"] == "unknown"


def test_a_link_object_url_is_resolved():
    entry = {"type": "Image", "url": {"type": "Link", "href": "https://r.example/l.png"}}

    assert media_attachments_from_attachment([entry])[0]["url"] == "https://r.example/l.png"


def test_a_list_of_links_takes_the_first_usable_href():
    entry = {"url": [{"type": "Link"}, {"href": "https://r.example/first.png"}]}

    assert media_attachments_from_attachment([entry])[0]["url"] == "https://r.example/first.png"


def test_an_attachment_without_a_url_is_skipped():
    assert media_attachments_from_attachment([{"type": "Document", "mediaType": "image/png"}]) == []


def test_a_non_dict_attachment_is_skipped():
    assert media_attachments_from_attachment(["kaputt", 5, None]) == []


def test_an_empty_attachment_list_yields_no_media():
    assert media_attachments_from_attachment([]) == []


def test_from_activity_reads_media_from_the_object():
    activity = {"actor": "https://r.example/actors/dave",
                "object": {"content": "hi", "attachment": [IMAGE_ATTACHMENT]}}

    status = Status.from_activity(activity, id="42")

    assert status.media_attachments[0]["url"] == "https://r.example/media/1.jpg"


def test_from_activity_without_media_leaves_the_list_empty():
    activity = {"actor": "https://r.example/actors/dave", "object": {"content": "hi"}}

    assert Status.from_activity(activity, id="42").media_attachments == []


def test_placeholder_account_uses_the_heuristic_acct():
    account = placeholder_account("https://other.example/users/zoe")

    assert account.acct == "zoe@other.example"
    assert account.username == "zoe"

