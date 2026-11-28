#!/bin/bash
set -e
cd "$(dirname "$0")"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
BASE="https://raw.githubusercontent.com/StudyPilotCreator/StudyPilot/main/clipilot"

echo "ClipPilot wird aktualisiert..."
for file in server.py index.html mobile.html requirements.txt Install_ClipPilot.command Start_ClipPilot.command README_LOCAL.md; do
  echo "Aktualisiere $file ..."
  curl --fail --location --silent --show-error "$BASE/$file" -o "$file"
done

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew wurde nicht gefunden. Bitte zuerst Homebrew installieren."
  exit 1
fi

brew install ffmpeg python@3.13 deno
PYTHON_BIN="$(command -v python3.13 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3.13 wurde nicht gefunden."
  exit 1
fi

if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  BACKUP=".venv-backup-$(date +%Y%m%d-%H%M%S)"
  echo "Sichere alte Python-Umgebung nach $BACKUP"
  mv .venv "$BACKUP"
fi

if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install --upgrade -r requirements.txt "yt-dlp[default]"

echo ""
echo "Update abgeschlossen."
echo "yt-dlp-Version: $(./.venv/bin/python -m yt_dlp --version)"
echo "Deno-Version: $(deno --version | head -n 1)"
echo ""
echo "Jetzt ClipPilot mit bash Start_ClipPilot.command neu starten."
