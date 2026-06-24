# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
import nh3


_TAGS = {
    "p", "br", "span", "a", "abbr", "del", "pre", "blockquote", "code",
    "b", "strong", "u", "sub", "sup", "i", "em",
    "h1", "h2", "h3", "h4", "h5", "ul", "ol", "li",
}
_ATTRIBUTES = {
    "a": {"href", "class", "translate"},
    "span": {"class", "translate"},
    "abbr": {"title"},
    "blockquote": {"cite"},
    "ol": {"start", "reversed"},
    "li": {"value"},
}
_URL_SCHEMES = {
    "http", "https", "dat", "dweb", "ipfs", "ipns",
    "ssb", "gopher", "xmpp", "magnet", "gemini",
}
_LINK_REL = "nofollow noopener noreferrer"
_ALLOWED_CLASS = re.compile(r"^(?:h|p|u|dt|e)-|^(?:mention|hashtag)$")


def _filter_attribute(tag, attribute, value):
    if attribute == "class":
        return " ".join(c for c in value.split() if _ALLOWED_CLASS.match(c)) or None
    return value


def sanitize_html(html):
    return (nh3.clean(html,
                      tags=_TAGS,
                      attributes=_ATTRIBUTES,
                      url_schemes=_URL_SCHEMES,
                      link_rel=_LINK_REL,
                      attribute_filter=_filter_attribute,
                      clean_content_tags={"script", "style"})
            if html else
            html)

