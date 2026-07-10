# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import ClassVar

from .actor import Actor


def _image(url):
    return {"type": "Image", "url": url} if url else None


class Application(Actor):
    _base_context: ClassVar[list[str | dict[str, str]]] = \
            ["https://www.w3.org/ns/activitystreams",
             "https://w3id.org/security/v1"]

    type: str = "Application"
    name: str | None = None
    summary: str | None = None
    icon: dict | None = None
    image: dict | None = None
    inbox: str
    publicKey: dict | None = None

    @classmethod
    def from_state(cls, state: dict, actor_url: str) -> "Application":
        return cls(id=actor_url,
                   preferredUsername=state["preferredUsername"],
                   name=state.get("name"),
                   summary=state.get("summary"),
                   inbox=f"{actor_url}/inbox",
                   publicKey={"id": f"{actor_url}#main-key",
                              "type": "Key",
                              "owner": actor_url,
                              "publicKeyPem": state["public_key_pem"]},
                   icon=_image(state.get("icon")),
                   image=_image(state.get("image")))

