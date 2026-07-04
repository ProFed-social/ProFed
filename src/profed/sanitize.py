# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import re
from html import unescape
import nh3


logger = logging.getLogger(__name__)

_TAGS = {
    "p", "br", "span", "a", "abbr", "del", "pre", "blockquote", "code",
    "b", "strong", "u", "sub", "sup", "i", "em", "small",
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
_AS2_HTML_FIELDS = frozenset({"content", "summary"})
_HTML_SUBTREES = {"resume": frozenset({"description"})}
_DANGEROUS_SCHEME = re.compile(r".*script.*|data|blob|file", re.IGNORECASE)

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


def _dangerous_scheme(text):
    match = re.match(r"([a-zA-Z][a-zA-Z0-9+.-]*):",
                     re.sub(r"^[\x00-\x20]+", "", re.sub(r"[\t\r\n]", "", text)))
    if match is not None and _DANGEROUS_SCHEME.fullmatch(match.group(1)):
        logger.warning("strip_tags: dropped value with disallowed URL scheme %r", match.group(1))
        return True
    return False


def strip_tags(text):
    if not text:
        return text
    previous = None
    result = text
    while result != previous:
        previous = result
        result = unescape(nh3.clean(result, tags=set(), clean_content_tags={"script", "style"}))
    return "" if _dangerous_scheme(result) else result


def _html_value(value):
    return (sanitize_html(value)
            if isinstance(value, str) else
            {key: _html_value(v) for key, v in value.items()}
            if isinstance(value, dict) else
            [_html_value(v) for v in value]
            if isinstance(value, list) else
            value)


def sanitize_document(value, html_fields=_AS2_HTML_FIELDS):
    return ({key: (_html_value(v)
                   if (key[:-3] if key.endswith("Map") else key) in html_fields else
                   sanitize_document(v, html_fields | _HTML_SUBTREES[key])
                   if key in _HTML_SUBTREES else
                   sanitize_document(v, html_fields))
             for key, v in value.items()}
            if isinstance(value, dict) else
            [sanitize_document(v, html_fields) for v in value]
            if isinstance(value, list) else
            strip_tags(value)
            if isinstance(value, str) else
            value)

