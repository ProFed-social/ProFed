# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import ClassVar

from profed.identity import actor_url_from_username
from profed.core.media_storage import media_storage
from profed.models.resume import Resume
from profed.models.user_profile import UserProfile

from .actor import Actor


def _image_object(ref, variant):
    return ({"type": "Image",
             "url": media_storage().url_for(ref.media_id,
                                            (variant
                                             if variant in ref.variants else
                                             None))}
            if ref is not None else
            None)


class Person(Actor):
    _base_context: ClassVar[list[str | dict[str, str]]] = \
            ["https://www.w3.org/ns/activitystreams",
             {"profed": "https://profed.social/ns#",
              "resume": "profed:resume"}]

    type: str = "Person"
    name: str | None = None
    summary: str | None = None
    icon:  dict | None = None
    image: dict | None = None
    inbox: str
    outbox: str
    resume: Resume | None = None
    publicKey: dict | None = None
    published: str | None = None

    @classmethod
    def from_user(cls, profile: UserProfile, published: str | None = None) -> "Person":
        actor_url = actor_url_from_username(profile.username)
        return cls(id=actor_url,
                   preferredUsername=profile.username,
                   name=profile.name,
                   summary=profile.summary,
                   resume=profile.resume,
                   inbox=f"{actor_url}/inbox",
                   outbox=f"{actor_url}/outbox",
                   publicKey=(None
                              if getattr(profile, "public_key_pem", None) is None else
                              {"id": f"{actor_url}#main-key",
                               "type": "Key",
                               "owner": actor_url,
                               "publicKeyPem": profile.public_key_pem}),
                   icon=_image_object(profile.avatar, "large"),
                   image=_image_object(profile.header, "wide"),
                   published=published)

