#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Erst Install_ClipPilot.command ausführen."
  read -p "Enter zum Beenden..."
  exit 1
fi
echo "ClipPilot Local startet. Dieses Terminal offen lassen."
echo "Die Website: https://studypilotcreator.github.io/StudyPilot/clipilot/"
echo "Token steht gleich hier im Terminal. In die Website eintragen."
./.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8765
