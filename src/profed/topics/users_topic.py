# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict
from profed.models import UserProfile, Resume, MediaReference


logger = logging.getLogger(__name__)


def _ignore_msg(msg):
    return f"Ignoring malformed users event: {msg}"


def _ignore_snp(msg):
    return f"Ignoring malformed users snapshot item: {msg}"


def _validate_created(payload):
    unknown = set(payload) - {"name",
                              "summary",
                              "resume",
                              "avatar",
                              "header",
                              "public_key_pem",
                              "private_key_pem"}
    if unknown:
        logger.warning(_ignore_msg(f"created has unknown fields: {unknown}"))
        return None

    try:
        return dict(payload, **{field: model.model_validate(payload[field]).model_dump()
                                for field, model in (("resume", Resume),
                                                     ("avatar", MediaReference),
                                                     ("header", MediaReference))
                                if field in payload})
    except Exception as exc:
        logger.warning(_ignore_msg(f"created has invalid payload: {exc}"))


def _validate_deleted(payload):
    if payload != {}:
        logger.warning(_ignore_msg(f"deleted payload must be empty: {payload!r}"))
        return None
    return {}


def _validate_profile_edited(payload):
    if not payload:
        logger.warning(_ignore_msg("profile_edited payload must not be empty"))
        return None

    def _is_types(types, key, value):
        if types is None:
            logger.warning(_ignore_msg(f"profile_edited has unknown field: {key}"))
        elif not isinstance(value, types):
            logger.warning(_ignore_msg(f"profile_edited field {key} has invalid type: {value!r}"))
        else:
            return True 

    return (dict(payload)
            if all(_is_types({"name": (str, type(None)),
                              "summary": (str, type(None)),
                              "fields": (list, type(None)),
                              "locked": (bool, type(None)),
                              "bot": (bool, type(None)),
                              "discoverable": (bool, type(None))}.get(key), key, value)
                   for key, value in payload.items()) else
            None)


def _validate_image_changed(payload):
    if payload == {}:
        return {}

    try:
        return MediaReference.model_validate(payload).model_dump()
    except Exception as exc:
        logger.warning(_ignore_msg(f"image_changed must be empty or a valid media reference: {payload!r}; {exc}"))


def _validate_cv_changed(payload):
    if payload == {} or set(payload) == {"resume"}:
        try:
            return ({"resume": Resume.model_validate(payload["resume"]).model_dump()}
                    if payload.get("resume") is not None else
                    {})
        except Exception as exc:
            logger.warning(_ignore_msg(f"cv_changed has invalid resume: {exc}"))
    else:
        logger.warning(_ignore_msg(f"cv_changed must be empty or contain only resume: {payload!r}"))


def _validate_keys_generated(payload):
    if set(payload) != {"public_key_pem", "private_key_pem"}:
        logger.warning(_ignore_msg(f"keys_generated must contain only public_key_pem and private_key_pem: {payload!r}"))
        return None

    def _has_key(key):
        return ((isinstance(payload[key], str) and payload[key]) or
                logger.warning(_ignore_msg(f"keys_generated {key} must be a non-empty string")))

    return ({"public_key_pem": payload["public_key_pem"],
             "private_key_pem": payload["private_key_pem"]}
            if _has_key("public_key_pem") and
               _has_key("private_key_pem") else
            None)


def validate_users_event(event_type: str, payload) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(_ignore_msg(f"payload is not a JSON object: {payload!r}"))
        return None

    def _unknown_event_type(payload) -> None:
        logger.warning(_ignore_msg(f"unknown event type {event_type!r}"))

    return ({"created": _validate_created,
             "updated": _validate_created,
             "deleted": _validate_deleted,
             "profile_edited": _validate_profile_edited,
             "avatar_changed": _validate_image_changed,
             "header_changed": _validate_image_changed,
             "cv_changed": _validate_cv_changed,
             "keys_generated": _validate_keys_generated}.get(event_type,
                                                             _unknown_event_type))(payload)


def validate_users_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore_snp(f"snapshot item is not a dict: {item!r}"))
        return None

    try:
        profile = UserProfile.model_validate(item)
    except Exception as exc:
        logger.warning(_ignore_snp(f"invalid snapshot item: {item!r}; {exc}"))
        return None

    return dict(profile.model_dump(exclude_none=True),
                **({"private_key_pem": profile.private_key_pem}
                   if profile.private_key_pem is not None else
                   {}))


topic = {"name":              "users",
         "validate":          validate_users_event,
         "snapshot_validate": validate_users_snapshot_item}

