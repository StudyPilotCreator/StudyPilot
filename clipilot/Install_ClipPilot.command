#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "ClipPilot Setup für Mac (Apple Silicon / Intel)"
echo "Installiere FFmpeg-full mit Untertitelfilter, Python 3.13 und Deno."

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew ist noch nicht installiert."
  echo "Installiere Homebrew über https://brew.sh/ und starte dieses Script danach erneut."
  read -p "Enter zum Beenden..."
  exit 1
fi

brew install ffmpeg-full python@3.13 deno
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

PYTHON_BIN="$(command -v python3.13 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3.13 wurde nicht gefunden. Bitte Homebrew-Installation prüfen."
  exit 1
fi

if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  BACKUP=".venv-backup-$(date +%Y%m%d-%H%M%S)"
  echo "Alte Python-Umgebung wird gesichert: $BACKUP"
  mv .venv "$BACKUP"
fi

if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install --upgrade -r requirements.txt "yt-dlp[default]"

echo ""
echo "Installierte Versionen:"
./.venv/bin/python -m yt_dlp --version
deno --version
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq '[[:space:]]subtitles[[:space:]]'; then
  echo "FEHLER: Der FFmpeg-Untertitelfilter ist nicht verfügbar."
  echo "Prüfe, ob ffmpeg-full installiert wurde."
  exit 1
fi
echo "FFmpeg-Untertitelfilter: verfügbar"

echo ""
echo "Installation fertig."
echo "Starte jetzt Start_ClipPilot.command"
