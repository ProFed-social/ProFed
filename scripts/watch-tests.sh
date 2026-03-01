#!/usr/bin/env bash
# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

source .venv/bin/activate || exit 1

# Colors for terminal background (ANSI OSC 11)
RED="\033]11;#FF0000\007"
GREEN="\033]11;#00FF00\007"

# Run pytest-watch continuously
ptw --onfail "printf '$RED'" \
    --onpass "printf '$GREEN'"
