#!/bin/bash
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

if [ ! -x .venv/bin/python ]; then
  echo "Bitte zuerst Install_ClipPilot.command ausführen."
  read -p "Enter zum Beenden..."
  exit 1
fi

MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
echo ""
echo "=========================================="
echo " ClipPilot startet"
echo "=========================================="
echo "Mac-Seite: http://127.0.0.1:8765"
if [ -n "$MAC_IP" ]; then
  echo "iPhone-Seite im selben WLAN: http://$MAC_IP:8765/mobile"
else
  echo "iPhone-Seite: http://MAC-IP:8765/mobile"
fi
echo ""
echo "YouTube-Engine:"
./.venv/bin/python -m yt_dlp --version || true
deno --version | head -n 1 || true
echo "FFmpeg: $(command -v ffmpeg)"
ffmpeg -hide_banner -filters 2>/dev/null | grep -E '[[:space:]]subtitles[[:space:]]' || {
  echo "FEHLER: FFmpeg hat keinen Untertitelfilter. Bitte Update_ClipPilot.command erneut ausführen."
  exit 1
}
echo ""
echo "Das Verbindungstoken wird gleich hier angezeigt."
echo "Einmal in der ClipPilot-Seite eintragen und speichern."
echo "Dieses Terminal während der Verarbeitung offen lassen."
echo "Zum Beenden: Ctrl + C"
echo ""

./.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8765
