# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Optional
from profed.models import Resume, UserProfile
from profed.sanitize import sanitize_html, strip_tags
from .composition import apply_template
 
 
DEFAULT_USERNAME = "{given-name}_{family-name}"
DEFAULT_NAME     = "{name|{given-name} {additional-name} {family-name}}"
DEFAULT_SUMMARY  = "{summary|{note}}"


def _first(lst: list, default=None) -> Any:
    return lst[0] if lst else default


def _from_val(value: any, get: Callable):
    return strip_tags(value
                      if isinstance(value, str) else
                      get(value)
                      if isinstance(value, dict) else
                      "").strip() or None


def _to_text(value: Any) -> Optional[str]:
    return _from_val(value, lambda v: (v.get("value") or v.get("html", "")).strip())


def _to_url(value: Any) -> Optional[str]:
    return _from_val(value, lambda v: v.get("value") or v.get("url"))


def _raw(value: Any) -> str:
    if isinstance(value, dict):
        return (value.get("html") or value.get("value") or "").strip()
    return value.strip() if isinstance(value, str) else ""
 
 
def _values(props: dict, hcard_props: dict) -> dict[str, str]:
    merged = {**hcard_props, **props}
    return {key: raw
            for key, raw in ((key, _raw(_first(vals))) for key, vals in merged.items())
            if raw}


def _html_field(props: dict, name: str) -> Optional[str]:
    for key in (name, "x-" + name):
        first = _first(props.get(key, []))
        if isinstance(first, dict) and first.get("html"):
            return sanitize_html(first["html"]) or None
    for key in (name, "x-" + name):
        text = _to_text(_first(props.get(key, [])))
        if text is not None:
            return text
    return None


def _reference(item: Any) -> dict:
    if not isinstance(item, dict):
        return {}
    props = item.get("properties", {})
    author = _first(props.get("author", []))
    aprops = author.get("properties", {}) if isinstance(author, dict) else {}
    giver = {key: value
             for key, value in (("name", _to_text(_first(aprops.get("name", [])))),
                                ("role", _to_text(_first(aprops.get("job-title", [])))),
                                ("organization", _to_text(_first(aprops.get("org", [])))))
             if value is not None}
    content = {(value.get("lang") or "und"): sanitize_html(value["html"])
               for value in props.get("content", [])
               if isinstance(value, dict) and value.get("html")}
    url = _to_url(_first(props.get("url", [])))
    verification = _to_text(_first(props.get("x-verification", [])))
    return {key: value
            for key, value in (("author", giver),
                               ("content", content),
                               ("url", url),
                               ("verification", verification))
            if value}


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
                               ("url", "url")]:
        val = _to_text(_first(props.get(mf2_key, [])))
        if val is not None:
            result[model_key] = val

    description = _html_field(props, "description")
    if description is not None:
        result["description"] = description

    technologies = [t for t in (_to_text(v) for v in props.get("technology", [])) if t is not None]
    if technologies:
        result["technologies"] = technologies

    organization = (_to_text(_first(props.get("org", [])))
                    or _to_text(_first(props.get("location", []))))
    if organization is not None:
        result["organization"] = organization

    return result


def _project_lookup(project_items) -> dict:
    return {item["id"]: name
            for item, name in ((item, _to_text(_first(item.get("properties", {}).get("name", []))))
                               for item in project_items
                               if isinstance(item, dict) and item.get("id"))
            if name}


def _linked_project_names(item, lookup) -> list:
    return ([name
             for name in (lookup.get(url.rsplit("#", 1)[-1])
                          for url in item.get("properties", {}).get("x-project", [])
                          if isinstance(url, str) and "#" in url)
             if name]
            if isinstance(item, dict) else
            [])



def normalize_mf2_to_profile(mf2_data: dict,
                             username_template: str = DEFAULT_USERNAME,
                             name_template: str = DEFAULT_NAME,
                             summary_template: str = DEFAULT_SUMMARY) -> tuple[UserProfile, dict[str, str | None]] | None:
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
    values = _values(props, hcard_props)
    username = " ".join(apply_template(username_template, values).split())
    if not username:
        return None

    name = " ".join(apply_template(name_template, values).split()) or None
    summary = sanitize_html(apply_template(summary_template, values)) or None
    def to_resume(h_resume):
        if h_resume is None:
            return None

        rprops = h_resume.get("properties", {})
        project_items = rprops.get("x-project", []) or rprops.get("project", [])

        lookup = _project_lookup(project_items)
        def experience_entry(item):
            entry = _normalize_entry(item)
            if entry:
                names = _linked_project_names(item, lookup)
                if names:
                    entry["projects"] = names
            return entry

        return Resume(experience=[e for e in (experience_entry(x) for x in rprops.get("experience", [])) if e],
                      education=[e for e in (_normalize_entry(x) for x in rprops.get("education",  [])) if e],
                      skills=[{"name": s} for s in (t for t in (_to_text(v) for v in rprops.get("skill", [])) if t is not None)],
                      projects=[e for e in (_normalize_entry(x) for x in project_items) if e],
                      references=[r for r in (_reference(c)
                                              for c in h_resume.get("children", [])
                                              if isinstance(c, dict) and "h-cite" in c.get("type", []))
                                  if r])

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

