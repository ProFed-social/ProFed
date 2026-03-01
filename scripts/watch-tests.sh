#!/usr/bin/env bash

# Activate virtual environment
source .venv/bin/activate || exit 1

# Colors for terminal background (ANSI OSC 11)
RED="\033]11;#FF0000\007"
GREEN="\033]11;#00FF00\007"

# Run pytest-watch continuously
ptw --onfail "printf '$RED'" \
    --onpass "printf '$GREEN'"
