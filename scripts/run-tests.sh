#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  echo "Virtualenv not found. Run: uv venv && uv pip install -e .[dev]"
  exit 1
fi

source .venv/bin/activate
pytest "$@"
