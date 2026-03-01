#!/usr/bin/env bash
set -e

uv venv
source .venv/bin/activate
uv pip install -e .
uv pip install pytest pytest-watch

