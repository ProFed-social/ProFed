#!/usr/bin/env bash
# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
  echo "Virtualenv not found. Run: scripts/bootstrap.sh"
  exit 1
fi

if [ ! -d "client/node_modules" ]; then
  echo "Client dependencies not found. Run: scripts/bootstrap.sh"
  exit 1
fi

source .venv/bin/activate

status=0
echo "== Python (pytest) =="
pytest "$@" || status=1
echo "== Web client (vitest) =="
( cd client && npm test ) || status=1
exit $status

