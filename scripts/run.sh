#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ ! -x .venv/bin/vibe-viewer ]]; then
  make install
fi

exec .venv/bin/vibe-viewer "$@"
