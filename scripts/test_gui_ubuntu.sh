#!/usr/bin/env bash
set -euo pipefail

display_number=99
display=":${display_number}"
socket="/tmp/.X11-unix/X${display_number}"

Xvfb "$display" -screen 0 1440x900x24 -nolisten tcp &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT

for _ in {1..100}; do
  [[ -S "$socket" ]] && break
  sleep 0.05
done

if [[ ! -S "$socket" ]]; then
  echo "Xvfb не создал дисплей ${display}." >&2
  exit 1
fi

if [[ "$#" -gt 0 ]]; then
  DISPLAY="$display" "$@"
else
  DISPLAY="$display" pytest -q tests/test_main_window.py tests/test_rich_formats.py
fi
