#!/usr/bin/env bash
# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

set -e

uv venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]

cd "$PROJECT_ROOT/client"
npm ci

