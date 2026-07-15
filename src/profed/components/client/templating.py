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


def build_environment(standard_dir, theme_dir):
    environment = Environment(loader=build_loader(standard_dir, theme_dir),
                              autoescape=select_autoescape(["html", "xml"]))
    environment.filters["sanitize"] = sanitize_html
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

