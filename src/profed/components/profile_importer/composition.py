# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


def _split_tag(body: str) -> tuple[str, str, str]:
    level = 1
    for pos, c in enumerate(body):
        level += (c == "{") - (c == "}")
        if level == 0:
            name, _, default = body[:pos].partition("|")
            return name.strip(), default, body[pos + 1:]
    raise ValueError(f"unbalanced template tag: {{{body}")


def apply_template(template: str, values: dict[str, str]) -> str:
    head, tail = "", template
    while "{" in tail:
        text, _, tail = tail.partition("{")
        name, default, tail = _split_tag(tail)
        head, tail = ((head + text + values[name], tail)
                      if name in values else
                      (head + text, default + tail))
    return head + tail

