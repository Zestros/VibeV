#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Для установки системных пакетов нужен root или sudo." >&2
  exit 1
fi

"${sudo_cmd[@]}" apt-get update
"${sudo_cmd[@]}" apt-get install -y \
  make \
  python3 python3-venv python3-pip \
  fonts-dejavu-core fonts-liberation \
  libdbus-1-3 libegl1 libfontconfig1 libgl1 libgl1-mesa-dri \
  libglib2.0-0 libnss3 libpulse0 libva2 libva-x11-2 \
  libx11-xcb1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xfixes0 libxcb-xinerama0

make install

echo "Установка завершена. Запуск: make run"
