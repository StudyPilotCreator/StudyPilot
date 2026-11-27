#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "ClipPilot Setup für Mac (Apple Silicon / Intel)"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew ist noch nicht installiert."
  echo "Installiere Homebrew über https://brew.sh/ und starte dieses Script danach erneut."
  read -p "Enter zum Beenden..."
  exit 1
fi

brew install ffmpeg
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install --upgrade -r requirements.txt
./.venv/bin/pip install --upgrade yt-dlp

echo ""
echo "Installation fertig."
echo "Starte jetzt Start_ClipPilot.command"
