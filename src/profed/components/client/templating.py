# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from markupsafe import escape

from profed.core.config import config
from profed.identity import domain
from profed.sanitize import sanitize_html


STANDARD_TEMPLATES = Path(__file__).parent / "templates"

_instance = None


def build_loader(standard_dir, theme_dir):
    return ChoiceLoader([FileSystemLoader(str(d))
                         for d in ([theme_dir, standard_dir]
                                   if theme_dir else
                                   [standard_dir])])


def rfc822(timestamp: str) -> str:
    try:
        return format_datetime(datetime.fromisoformat(timestamp))
    except (TypeError, ValueError):
        return ""


_RELATIVE_STEPS = ((60, "a minute", "minutes", 1),
                   (24, "an hour", "hours", 60),
                   (7, "a day", "days", 1440),
                   (4, "a week", "weeks", 10080),
                   (12, "a month", "months", 43200))


def _parsed(timestamp: str):
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _phrase(count: int, singular: str, plural: str) -> str:
    return f"{singular} ago" if count == 1 else f"{count} {plural} ago"


def relative_time(timestamp: str, now=None) -> str:
    parsed = _parsed(timestamp)
    if parsed is None:
        return ""

    minutes = int(((now or datetime.now(timezone.utc)) - parsed).total_seconds() // 60)
    if minutes < 1:
        return "just now"

    for limit, singular, plural, factor in _RELATIVE_STEPS:
        if minutes // factor < limit:
            return _phrase(minutes // factor, singular, plural)

    return _phrase(minutes // 525600, "a year", "years")


def local_minutes(timestamp: str) -> str:
    parsed = _parsed(timestamp)
    return parsed.strftime("%Y-%m-%d %H:%M") if parsed else ""


def profile_href(account) -> str:
    acct = (account or {}).get("acct")
    return f"https://{domain()}/@{acct}" if acct else (account or {}).get("url", "")


def link_field(value: str) -> str:
    return (f'<a rel="me" href="{escape(value)}">{escape(value)}</a>'
            if value.startswith("https://") or value.startswith("http://") else
            sanitize_html(value))


def build_environment(standard_dir, theme_dir):
    environment = Environment(loader=build_loader(standard_dir, theme_dir),
                              autoescape=select_autoescape(["html", "xml"]))
    environment.filters.update(sanitize=sanitize_html,
                               link_field=link_field,
                               profile_href=profile_href,
                               rfc822=rfc822,
                               relative_time=relative_time,
                               local_minutes=local_minutes)
    return environment


def environment():
    global _instance

    if _instance is None:
        _instance = build_environment(STANDARD_TEMPLATES,
                                      config().get("client", {}).get("theme_dir"))

    return _instance


def _reset_environment():
    global _instance
    _instance = None

