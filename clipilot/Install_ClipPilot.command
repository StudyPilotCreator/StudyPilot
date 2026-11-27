#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "ClipPilot Local setup für Mac (Apple Silicon/Intel)"
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew fehlt. Bitte zuerst Homebrew installieren: https://brew.sh/"
  exit 1
fi
brew install ffmpeg
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
echo
echo "Installation fertig. Starte nun Start_ClipPilot.command"
