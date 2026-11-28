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

brew install ffmpeg-full python@3.13 deno
FFMPEG_FULL_PREFIX="$(brew --prefix ffmpeg-full 2>/dev/null || true)"
if [ -n "$FFMPEG_FULL_PREFIX" ] && [ -x "$FFMPEG_FULL_PREFIX/bin/ffmpeg" ]; then
  export PATH="$FFMPEG_FULL_PREFIX/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
else
  echo "FEHLER: Homebrew hat ffmpeg-full nicht gefunden."
  brew info ffmpeg-full
  exit 1
fi
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
# Explicitly replace any pre-existing PyAV 19 installation.
./.venv/bin/python -m pip install --force-reinstall --no-cache-dir "av==18.1.0"

echo ""
echo "Update abgeschlossen."
echo "yt-dlp-Version: $(./.venv/bin/python -m yt_dlp --version)"
echo "Deno-Version: $(deno --version | head -n 1)"
echo "FFmpeg-Version: $(ffmpeg -version | head -n 1)"
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq '[[:space:]]subtitles[[:space:]]'; then
  echo "FEHLER: FFmpeg-full wurde gefunden, aber der Untertitelfilter fehlt."
  exit 1
fi
echo "FFmpeg-Untertitelfilter: verfügbar"
echo "Verwendetes FFmpeg: $(command -v ffmpeg)"
echo ""
echo "Jetzt ClipPilot mit bash Start_ClipPilot.command neu starten."
