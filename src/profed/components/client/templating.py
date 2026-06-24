# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from profed.core.config import config
from profed.sanitize import sanitize_html


STANDARD_TEMPLATES = Path(__file__).parent / "templates"

_instance = None


def build_loader(standard_dir, theme_dir):
    return ChoiceLoader([FileSystemLoader(str(d))
                         for d in ([theme_dir, standard_dir]
                                   if theme_dir else
                                   [standard_dir])])


def environment():
    global _instance

    if _instance is None:
        theme_dir = config().get("client", {}).get("theme_dir")
        _instance = Environment(loader=build_loader(STANDARD_TEMPLATES, theme_dir),
                                autoescape=select_autoescape(["html", "xml"]))
        _instance.filters["sanitize"] = sanitize_html

    return _instance


def _reset_environment():
    global _instance
    _instance = None

