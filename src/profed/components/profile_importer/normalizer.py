# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Any, Optional
from profed.models import Resume, UserProfile
 
 
def _first(lst: list, default=None) -> Any:
    return lst[0] if lst else default
 
 
def _to_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        raw = value.get("value") or value.get("html", "")
        return raw.strip() or None
    return None


def _to_url(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return value.get("value") or value.get("url")
    return None

 
def _normalize_entry(item: Any) -> dict:
    if isinstance(item, str):
        return {"name": item.strip()} if item.strip() else {}
    if not isinstance(item, dict):
        return {}

    props = item.get("properties", {})
    result: dict = {}
    for mf2_key, model_key in [("name", "name"),
                               ("start", "start"),
                               ("end", "end"),
                               ("description", "description"),
                               ("url", "url")]:
        val = _to_text(_first(props.get(mf2_key, [])))
        if val is not None:
            result[model_key] = val

    organization = (_to_text(_first(props.get("org", [])))
                    or _to_text(_first(props.get("location", []))))
    if organization is not None:
        result["organization"] = organization

    return result
 
 
def normalize_mf2_to_profile(mf2_data: dict, username: str) -> tuple[UserProfile, dict[str, str | None]] | None:
    items = mf2_data.get("items", [])
    if not items:
        return None

    h_resume = next((i for i in items if "h-resume" in i.get("type", [])), None)
    primary = h_resume or next((i for i in items if "h-card" in i.get("type", [])), None)
    if primary is None:
        return None

    props   = primary.get("properties", {})
    contact = props.get("contact", [])
    hcard_props = (contact[0].get("properties", {})
                   if contact and isinstance(contact[0], dict)
                   else {})
    name = (_to_text(_first(props.get("name", [])))
            or _to_text(_first(hcard_props.get("name", []))))
    summary = _to_text(_first(props.get("summary", [])
                              or props.get("note", [])
                              or hcard_props.get("summary", [])
                              or hcard_props.get("note", [])))
    def to_resume(h_resume):
        if h_resume is None:
            return None

        rprops = h_resume.get("properties", {})
        return Resume(experience=[e for e in (_normalize_entry(x) for x in rprops.get("experience", [])) if e],
                      education=[e for e in (_normalize_entry(x) for x in rprops.get("education",  [])) if e],
                      skills=[{"name": s} for s in (t for t in (_to_text(v) for v in rprops.get("skill", [])) if t is not None)],
                      projects=[e for e in (_normalize_entry(x) for x in (rprops.get("x-project", []) or rprops.get("project", []))) if e])

    return (UserProfile(username=username,
                        name=name,
                        summary=summary,
                        resume=to_resume(h_resume)),
            {"avatar": _to_url(_first(props.get("photo", []))) or
                       _to_url(_first(hcard_props.get("photo", []))),
             "header": _to_url(_first(props.get("featured",  []))) or
                       _to_url(_first(hcard_props.get("featured",  []))) or
                       _to_url(_first(props.get("x-header",  []))) or
                       _to_url(_first(hcard_props.get("x-header",  [])))})

