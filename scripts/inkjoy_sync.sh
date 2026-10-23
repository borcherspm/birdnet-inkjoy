#!/usr/bin/env bash
# Wrapper to run the Python InkJoy sync tool
exec python3 "$(dirname "$0")/inkjoy_bridge.py" "$@"
