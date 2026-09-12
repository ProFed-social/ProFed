# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .emoji import base_of, tone_of


def _counted(rows):
    return {base: sum(row["n_of_uses"] for row in rows if base_of(row["emoji"]) == base)
            for base in {base_of(row["emoji"]) for row in rows}}


def from_history(payload):
    return {"reactions": _counted(payload.get("counts", [])),
            "tone": tone_of(payload.get("last_toned") or "")}

def quick_access(counts, defaults):
    ranked = sorted(counts, key=lambda emoji: (-counts[emoji], emoji))[:len(defaults)]
    return ranked + [default for default in defaults if default not in ranked][:len(defaults) - len(ranked)]


def _shifted(counts, emoji, delta):
    base = base_of(emoji)
    return {name: total for name, total in {**counts, base: counts.get(base, 0) + delta}.items() if total > 0}


def after_react(state, emoji, previous):
    counts = state.get("reactions", {})
    return {"reactions": _shifted(_shifted(counts, previous, -1) if previous else counts, emoji, 1),
            "tone": tone_of(emoji) or state.get("tone", "")}


def after_unreact(state, emoji):
    return {"reactions": _shifted(state.get("reactions", {}), emoji, -1), "tone": state.get("tone", "")}

